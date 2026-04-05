"""背景 Worker — 每 5 秒輪詢 notification_queue
讀取 → enrich → 查收件人/偏好 → 渲染模板 → publish 到 SQS → 寫 log
"""

import json
import asyncio
import logging
from app.models.notification_event import NotificationEventType
from app.services.notification_service import notification_service
from app.config import settings

logger = logging.getLogger(__name__)

# event_type → 需查哪些 entity 欄位作為收件人
# booking 事件的教師收件人由 _resolve_booking_teacher_col() 動態決定
_RECIPIENT_ENTITY_COLS: dict[str, list[str]] = {
    "booking.confirmed": ["student_id", "_booking_teacher"],
    "booking.cancelled": ["student_id", "_booking_teacher"],
    "contract.activated": ["student_id"],
    "contract.terminated": ["student_id"],
    "contract.converted": ["student_id"],
}


def _resolve_booking_teacher_col(payload: dict) -> str:
    """有代課教師時通知代課教師，否則通知原教師"""
    if payload.get("substitute_teacher_id"):
        return "substitute_teacher_id"
    return "teacher_id"

# payload 需要 enrich 的名稱欄位
_ENRICH_FIELDS = {
    "student_id": ("students", "name", "student_name"),
    "teacher_id": ("teachers", "name", "teacher_name"),
    "substitute_teacher_id": ("teachers", "name", "substitute_teacher_name"),
    "course_id": ("courses", "course_name", "course_name"),
}


_poll_count = 0

async def process_notification_queue():
    """從 queue 取出 pending 事件，逐筆處理"""
    global _poll_count
    if not settings.NOTIFICATION_ENABLED:
        return

    # 每 100 次 poll（約 8 分鐘）清理一次過期 queue 項目
    _poll_count += 1
    if _poll_count % 100 == 0:
        try:
            from app.services.supabase_service import supabase_service
            await supabase_service.pool.execute("SELECT fn_cleanup_notification_queue()")
        except Exception:
            pass

    from app.services.supabase_service import supabase_service
    pool = supabase_service.pool

    # 原子性領取（防止重複處理）
    rows = await pool.fetch("""
        UPDATE notification_queue
        SET status = 'processing', processed_at = NOW()
        WHERE id IN (
            SELECT id FROM notification_queue
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT 20
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id, event_type, reference_id, reference_type, payload
    """)

    if not rows:
        return

    for row in rows:
        queue_id = row["id"]
        event_type = row["event_type"]
        ref_id = str(row["reference_id"])
        ref_type = row["reference_type"]
        payload = row["payload"] or {}

        try:
            # 1. 驗證事件類型
            try:
                evt_enum = NotificationEventType(event_type)
            except ValueError:
                logger.warning(f"Unknown event type: {event_type}, skipping")
                await pool.execute(
                    "UPDATE notification_queue SET status = 'done' WHERE id = $1", queue_id
                )
                continue

            cfg = notification_service.get_config(evt_enum)
            if not cfg:
                await pool.execute(
                    "UPDATE notification_queue SET status = 'done' WHERE id = $1", queue_id
                )
                continue

            # 2. enrich payload（補名稱）
            enriched = await _enrich_payload(pool, payload)

            # 3. 解析收件人（booking 事件動態決定教師欄位）
            raw_cols = _RECIPIENT_ENTITY_COLS.get(event_type, [])
            entity_cols = []
            for col in raw_cols:
                if col == "_booking_teacher":
                    entity_cols.append(_resolve_booking_teacher_col(payload))
                else:
                    entity_cols.append(col)
            recipients = await notification_service.resolve_recipients(entity_cols, payload)

            if not recipients:
                await pool.execute(
                    "UPDATE notification_queue SET status = 'done' WHERE id = $1", queue_id
                )
                continue

            # 4. 批次查偏好
            user_ids = [r["user_id"] for r in recipients]
            prefs = await notification_service.batch_check_preferences(user_ids, cfg["pref_key"])

            # 5. 對每個收件人：渲染 → publish SQS → log
            for recipient in recipients:
                user_id = recipient["user_id"]
                email = recipient["email"]
                name = recipient["name"]

                if not prefs.get(user_id, True):
                    continue

                # 渲染模板
                subject, html_body = notification_service.render_email(evt_enum, name, enriched)

                # Publish 到 SQS
                sqs_status = await _publish_to_sqs({
                    "to_email": email,
                    "subject": subject,
                    "html_body": html_body,
                    "event_type": event_type,
                    "reference_id": ref_id,
                    "user_id": user_id,
                })

                # 寫入 notification_logs
                await notification_service.log_notification(
                    user_id=user_id,
                    email=email,
                    event_type=event_type,
                    subject=subject,
                    status="queued" if sqs_status else "failed",
                    reference_id=ref_id,
                    reference_type=ref_type,
                    error_message=None if sqs_status else "SQS publish failed",
                )

            # 5. 標記完成
            await pool.execute(
                "UPDATE notification_queue SET status = 'done' WHERE id = $1", queue_id
            )

        except Exception as e:
            logger.error(f"Process queue item {queue_id} failed: {e}")
            await pool.execute(
                "UPDATE notification_queue SET status = 'failed' WHERE id = $1", queue_id
            )


_sqs_client = None

def _get_sqs_client():
    global _sqs_client
    if _sqs_client is None:
        import boto3
        _sqs_client = boto3.client(
            "sqs",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    return _sqs_client


async def _publish_to_sqs(message: dict) -> bool:
    """發送訊息到通知 SQS queue"""
    if not settings.NOTIFICATION_SQS_QUEUE_URL:
        logger.info(f"[DRY-RUN] SQS publish to={message.get('to_email')} subject={message.get('subject')}")
        return True

    loop = asyncio.get_event_loop()
    try:
        client = _get_sqs_client()
        await loop.run_in_executor(None, lambda: client.send_message(
            QueueUrl=settings.NOTIFICATION_SQS_QUEUE_URL,
            MessageBody=json.dumps(message, ensure_ascii=False),
        ))
        return True
    except Exception as e:
        logger.error(f"SQS publish failed: {e}")
        return False


async def _enrich_payload(pool, payload: dict) -> dict:
    """為 payload 補上名稱欄位（單一 SQL）"""
    import uuid as _uuid
    enriched = dict(payload)

    # 收集需要 enrich 的 ID
    ids_to_fetch = {}
    for id_col, (table, name_col, output_key) in _ENRICH_FIELDS.items():
        entity_id = payload.get(id_col)
        if entity_id and output_key not in enriched:
            ids_to_fetch[id_col] = (table, name_col, output_key, entity_id)

    if ids_to_fetch:
        # 用一條 SQL 批次查（UNION ALL）
        parts = []
        params = []
        idx = 0
        for id_col, (table, name_col, output_key, entity_id) in ids_to_fetch.items():
            idx += 1
            parts.append(f"SELECT '{output_key}' AS key, {name_col}::text AS val FROM {table} WHERE id = ${idx}")
            params.append(_uuid.UUID(str(entity_id)))

        if parts:
            try:
                sql = " UNION ALL ".join(parts)
                rows = await pool.fetch(sql, *params)
                for r in rows:
                    enriched[r["key"]] = r["val"] or ""
            except Exception:
                for _, (_, _, output_key, _) in ids_to_fetch.items():
                    enriched.setdefault(output_key, "")

    # 日期/時間轉字串
    for key in ("booking_date", "start_date", "end_date"):
        if key in enriched and enriched[key] is not None:
            enriched[key] = str(enriched[key])
    for key in ("start_time", "end_time"):
        if key in enriched and enriched[key] is not None:
            enriched[key] = str(enriched[key])[:5]

    return enriched
