"""通知服務 — 查收件人 + 偏好 → 渲染模板 → 回傳 email payload（不自己寄送）"""

import os
import logging
from datetime import datetime
from typing import Optional
from jinja2 import Environment, FileSystemLoader
from app.models.notification_event import NotificationEventType

logger = logging.getLogger(__name__)

# 事件 → 模板 + 主旨
_EVENT_CONFIG: dict[str, dict] = {
    NotificationEventType.BOOKING_CONFIRMED: {
        "template": "booking_confirmed.html",
        "subject": "課程預約已確認",
        "header": "預約確認通知",
        "pref_key": "booking_confirmed",
    },
    NotificationEventType.BOOKING_CANCELLED: {
        "template": "booking_cancelled.html",
        "subject": "課程預約已取消",
        "header": "預約取消通知",
        "pref_key": "booking_cancelled",
    },
    NotificationEventType.CONTRACT_ACTIVATED: {
        "template": "contract_activated.html",
        "subject": "您的課程合約已啟動",
        "header": "合約啟動通知",
        "pref_key": "contract_activated",
    },
    NotificationEventType.CONTRACT_CONVERTED: {
        "template": "contract_converted.html",
        "subject": "恭喜！試上已轉為正式課程",
        "header": "試上轉正通知",
        "pref_key": "contract_converted",
    },
    NotificationEventType.CONTRACT_TERMINATED: {
        "template": "contract_terminated.html",
        "subject": "合約終止通知",
        "header": "合約終止通知",
        "pref_key": "contract_terminated",
    },
}

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "email")
_jinja_env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=True)


class NotificationService:
    def get_config(self, event_type: NotificationEventType) -> Optional[dict]:
        return _EVENT_CONFIG.get(event_type)

    async def resolve_recipients(self, entity_cols: list[str], payload: dict) -> list[dict]:
        """從 payload 中的 entity id 查出 user_id + email + name（單一 SQL）

        Returns:
            list of {user_id, email, name}
        """
        from app.services.supabase_service import supabase_service
        import uuid as _uuid
        pool = supabase_service.pool

        # 收集所有需要查詢的條件
        conditions = []
        params = []
        idx = 0
        for col in entity_cols:
            entity_id = payload.get(col)
            if not entity_id:
                continue
            # col 只能是白名單內的欄位名
            if col not in ("student_id", "teacher_id", "employee_id", "substitute_teacher_id"):
                continue
            # substitute_teacher_id 在 user_profiles 中對應的是 teacher_id
            db_col = "teacher_id" if col == "substitute_teacher_id" else col
            idx += 1
            conditions.append(f"up.{db_col} = ${idx}")
            params.append(_uuid.UUID(str(entity_id)))

        if not conditions:
            return []

        try:
            where = " OR ".join(conditions)
            rows = await pool.fetch(f"""
                SELECT DISTINCT up.id AS user_id, u.email,
                       COALESCE(s.name, t.name, e.name) AS name
                FROM user_profiles up
                JOIN users u ON u.id = up.id
                LEFT JOIN students s ON s.id = up.student_id
                LEFT JOIN teachers t ON t.id = up.teacher_id
                LEFT JOIN employees e ON e.id = up.employee_id
                WHERE {where}
            """, *params)
            return [{
                "user_id": str(r["user_id"]),
                "email": r["email"],
                "name": r["name"] or r["email"],
            } for r in rows]
        except Exception as ex:
            logger.error(f"Resolve recipients failed: {ex}")
            return []

    async def check_preference(self, user_id: str, pref_key: str) -> bool:
        """檢查單一使用者通知偏好，預設啟用"""
        from app.services.supabase_service import supabase_service
        try:
            rows = await supabase_service.pool.fetch(
                f"SELECT email_enabled, {pref_key} FROM notification_preferences WHERE user_id = $1",
                __import__('uuid').UUID(user_id),
            )
            if not rows:
                return True
            return bool(rows[0]["email_enabled"]) and bool(rows[0][pref_key])
        except Exception:
            return True

    async def batch_check_preferences(self, user_ids: list[str], pref_key: str) -> dict[str, bool]:
        """批次檢查多個使用者的通知偏好，回傳 {user_id: enabled}"""
        import uuid as _uuid
        from app.services.supabase_service import supabase_service
        result = {uid: True for uid in user_ids}  # 預設啟用
        if not user_ids:
            return result
        try:
            uuids = [_uuid.UUID(uid) for uid in user_ids]
            placeholders = ", ".join(f"${i+1}" for i in range(len(uuids)))
            rows = await supabase_service.pool.fetch(
                f"SELECT user_id, email_enabled, {pref_key} FROM notification_preferences WHERE user_id IN ({placeholders})",
                *uuids,
            )
            for r in rows:
                uid = str(r["user_id"])
                result[uid] = bool(r["email_enabled"]) and bool(r[pref_key])
        except Exception:
            pass
        return result

    def render_email(self, event_type: NotificationEventType, recipient_name: str, data: dict) -> tuple[str, str]:
        """渲染 Email 模板，回傳 (subject, html_body)"""
        cfg = _EVENT_CONFIG.get(event_type)
        if not cfg:
            raise ValueError(f"No template config for {event_type}")

        template = _jinja_env.get_template(cfg["template"])
        html = template.render(
            header_title=cfg["header"],
            year=datetime.now().year,
            recipient_name=recipient_name,
            **data,
        )
        return f"[EOP] {cfg['subject']}", html

    async def log_notification(
        self,
        user_id: str,
        email: str,
        event_type: str,
        subject: str,
        status: str,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        from app.services.supabase_service import supabase_service
        try:
            await supabase_service.table_insert(
                table="notification_logs",
                data={
                    "user_id": user_id,
                    "recipient_email": email,
                    "channel": "email",
                    "event_type": event_type,
                    "subject": subject,
                    "notification_status": status,
                    "error_message": error_message,
                    "reference_id": reference_id,
                    "reference_type": reference_type,
                    "sent_at": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"Log notification failed: {e}")


notification_service = NotificationService()
