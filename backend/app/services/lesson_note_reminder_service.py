"""
課後筆記未上傳提醒服務

- 課程結束（booking_date + end_time）+ 12h 後尚未上傳筆記 → LINE 推老師
- 12-24h 之間每 3h 一次、最多 4 次（12 / 15 / 18 / 21h）
- 超過 24h 還沒上傳 → LINE 推 admin 一次

通知狀態追蹤在 lesson_note_reminders 表。
老師上傳筆記時 upload_lesson_note 會把 resolved_at 寫入，cron 自動跳過。
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.supabase_service import supabase_service
from app.services.line_message_service import line_message_service

logger = logging.getLogger(__name__)


# 排程常數
COURSE_END_GRACE_HOURS = 12
TEACHER_NOTIFY_INTERVAL_HOURS = 3
TEACHER_NOTIFY_MAX = 4
ADMIN_NOTIFY_THRESHOLD_HOURS = 24


class LessonNoteReminderService:

    async def scan_and_notify(self) -> dict:
        """主流程：掃描需要被通知的 booking 並推 LINE。回傳統計。

        TZ 注意：bookings.booking_date / end_time 是 naive 但業務語意=台北本地時間
        （與 docker-compose.yml backend TZ=Asia/Taipei 對齊）。本 service 用 naive
        Taipei 時間做 SQL 比較，再用 aware UTC 跟 lesson_note_reminders 的 TIMESTAMPTZ
        欄位比較。
        """
        try:
            now_naive = datetime.now()                  # naive Taipei，用於 naive 欄位比較
            now_utc = datetime.now(timezone.utc)        # aware UTC，用於 TIMESTAMPTZ 比較
            cutoff_12h_naive = now_naive - timedelta(hours=COURSE_END_GRACE_HOURS)

            sql = """
                SELECT
                    b.id AS booking_id,
                    b.booking_no,
                    b.teacher_id,
                    b.booking_date,
                    b.start_time,
                    b.end_time,
                    EXTRACT(EPOCH FROM ($1::timestamp - (b.booking_date + b.end_time))) / 3600
                        AS hours_since_end,
                    r.teacher_notified_count,
                    r.last_teacher_notified_at,
                    r.admin_notified_at
                FROM bookings b
                LEFT JOIN lesson_notes ln ON ln.booking_id = b.id
                LEFT JOIN lesson_note_reminders r ON r.booking_id = b.id
                WHERE b.is_deleted = FALSE
                  AND b.booking_status = 'confirmed'
                  AND ln.id IS NULL
                  AND (b.booking_date + b.end_time) <= $2
                  AND (r.resolved_at IS NULL)
            """
            rows = await supabase_service.pool.fetch(sql, now_naive, cutoff_12h_naive)

            teacher_notified = 0
            admin_notified = 0

            for row in rows:
                d = dict(row)
                hours_since = float(d["hours_since_end"])
                booking_id = str(d["booking_id"])

                if 12 <= hours_since < 24:
                    count = d.get("teacher_notified_count") or 0
                    last = d.get("last_teacher_notified_at")
                    if count < TEACHER_NOTIFY_MAX and (
                        last is None
                        or (now_utc - last) >= timedelta(hours=TEACHER_NOTIFY_INTERVAL_HOURS)
                    ):
                        await self._upsert_reminder_teacher(booking_id, count + 1, now_utc)
                        if await self._notify_teacher(d):
                            teacher_notified += 1

                if hours_since >= 24 and d.get("admin_notified_at") is None:
                    await self._upsert_reminder_admin(booking_id, now_utc)
                    if await self._notify_admins(d):
                        admin_notified += 1

            if teacher_notified or admin_notified:
                logger.info(
                    f"lesson_note reminder: teacher_notified={teacher_notified} "
                    f"admin_notified={admin_notified}"
                )
            return {"teacher_notified": teacher_notified, "admin_notified": admin_notified}
        except Exception as e:
            logger.error(f"scan_and_notify 失敗: {e}")
            return {"teacher_notified": 0, "admin_notified": 0}

    async def _upsert_reminder_teacher(
        self, booking_id: str, count: int, now: datetime
    ) -> None:
        sql = """
            INSERT INTO lesson_note_reminders
                (booking_id, teacher_notified_count, last_teacher_notified_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (booking_id) DO UPDATE SET
                teacher_notified_count = $2,
                last_teacher_notified_at = $3
        """
        await supabase_service.pool.execute(sql, booking_id, count, now)

    async def _upsert_reminder_admin(self, booking_id: str, now: datetime) -> None:
        sql = """
            INSERT INTO lesson_note_reminders (booking_id, admin_notified_at)
            VALUES ($1, $2)
            ON CONFLICT (booking_id) DO UPDATE SET
                admin_notified_at = $2
        """
        await supabase_service.pool.execute(sql, booking_id, now)

    async def _notify_teacher(self, booking: dict) -> bool:
        try:
            teacher_id = booking.get("teacher_id")
            if not teacher_id:
                return False
            line_user_id = await self._resolve_line_user_id_for_teacher(str(teacher_id))
            if not line_user_id:
                logger.info(
                    f"booking={booking.get('booking_id')}：老師未綁定 LINE，略過通知"
                )
                return False
            text = (
                "📝 課後筆記提醒\n"
                f"預約編號：{booking.get('booking_no')}\n"
                f"課程時間：{booking['booking_date']} "
                f"{booking['start_time']}-{booking['end_time']}\n"
                "此堂課已結束超過 12 小時但尚未上傳課後筆記，請盡快補上。"
            )
            result = await line_message_service.send_text_message(
                line_user_id, text, "teacher"
            )
            return bool(result)
        except Exception as e:
            logger.warning(f"通知老師失敗: {e}")
            return False

    async def _notify_admins(self, booking: dict) -> bool:
        """通知所有 admin（employee_subtype='admin' + 有 active employee channel LINE binding）"""
        try:
            sql = """
                SELECT DISTINCT lub.line_user_id
                FROM line_user_bindings lub
                JOIN user_profiles up ON up.id = lub.user_id
                WHERE up.employee_subtype = 'admin'
                  AND lub.channel_type = 'employee'
                  AND lub.binding_status = 'active'
            """
            rows = await supabase_service.pool.fetch(sql)
            if not rows:
                logger.info(
                    f"booking={booking.get('booking_id')}：無 active admin LINE binding"
                )
                return False
            text = (
                "⚠️ 課後筆記逾期未上傳\n"
                f"預約編號：{booking.get('booking_no')}\n"
                f"課程時間：{booking['booking_date']} "
                f"{booking['start_time']}-{booking['end_time']}\n"
                f"老師 ID：{booking.get('teacher_id')}\n"
                "已超過 24 小時未上傳，請追蹤"
            )
            any_sent = False
            for row in rows:
                try:
                    result = await line_message_service.send_text_message(
                        row["line_user_id"], text, "employee"
                    )
                    if result:
                        any_sent = True
                except Exception as e:
                    logger.warning(f"通知 admin {row['line_user_id']} 失敗: {e}")
            return any_sent
        except Exception as e:
            logger.warning(f"通知 admins 失敗: {e}")
            return False

    async def _resolve_line_user_id_for_teacher(self, teacher_id: str) -> Optional[str]:
        sql = """
            SELECT lub.line_user_id
            FROM line_user_bindings lub
            JOIN user_profiles up ON up.id = lub.user_id
            WHERE up.teacher_id = $1
              AND lub.channel_type = 'teacher'
              AND lub.binding_status = 'active'
            LIMIT 1
        """
        try:
            row = await supabase_service.pool.fetchrow(sql, teacher_id)
            return row["line_user_id"] if row else None
        except Exception as e:
            logger.warning(f"_resolve_line_user_id_for_teacher 失敗: {e}")
            return None


lesson_note_reminder_service = LessonNoteReminderService()
