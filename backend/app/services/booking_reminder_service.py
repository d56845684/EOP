"""
課前提醒服務（issue #73）

對 booking_status='confirmed' 的預約，在課程開始前 N 小時推 LINE 提醒
給 student 和 teacher。窗口由 settings.BOOKING_REMINDER_WINDOWS_HOURS 控制
（預設 24h, 1h），容忍區間由 BOOKING_REMINDER_TOLERANCE_MINUTES 控制。

防重複：booking_reminders 表 PK (booking_id, window, recipient)，
同一筆 booking 在每個窗口對每個對象只會推一次。

偏好過濾與通知日誌寫入由 line_message_service.send_booking_reminder() 負責。

TZ 注意：bookings.booking_date / start_time 是 naive，業務語意=台北本地時間，
與 docker-compose.yml backend TZ=Asia/Taipei 對齊。
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings
from app.services.supabase_service import supabase_service
from app.services.line_message_service import line_message_service

logger = logging.getLogger(__name__)


class BookingReminderService:

    async def scan_and_notify(self) -> dict:
        """主流程：掃描每個窗口內的 confirmed booking，對 student/teacher 推 LINE。"""
        try:
            windows = settings.booking_reminder_windows
            tolerance_min = settings.BOOKING_REMINDER_TOLERANCE_MINUTES
            now_naive = datetime.now()

            sent_total = 0
            failed_total = 0
            for hours in windows:
                target = now_naive + timedelta(hours=hours)
                lo = target - timedelta(minutes=tolerance_min)
                hi = target + timedelta(minutes=tolerance_min)
                window_label = f"{hours}h"

                stats = await self._scan_window(window_label, hours, lo, hi)
                sent_total += stats["sent"]
                failed_total += stats["failed"]

            if sent_total or failed_total:
                logger.info(
                    f"booking reminder scan: sent={sent_total} failed={failed_total}"
                )
            return {"sent": sent_total, "failed": failed_total}
        except Exception as e:
            logger.error(f"booking_reminder scan_and_notify 失敗: {e}")
            return {"sent": 0, "failed": 0}

    async def _scan_window(
        self, window_label: str, hours_before: int, lo: datetime, hi: datetime
    ) -> dict:
        sql = """
            SELECT
                b.id AS booking_id,
                b.booking_date,
                b.start_time,
                c.course_name,
                t.name AS teacher_name,
                s.name AS student_name,
                up_s.id AS student_user_id,
                up_t.id AS teacher_user_id,
                (br_s.booking_id IS NOT NULL) AS student_sent,
                (br_t.booking_id IS NOT NULL) AS teacher_sent
            FROM bookings b
            JOIN courses c ON c.id = b.course_id
            JOIN teachers t ON t.id = b.teacher_id
            JOIN students s ON s.id = b.student_id
            LEFT JOIN user_profiles up_s ON up_s.student_id = b.student_id
            LEFT JOIN user_profiles up_t ON up_t.teacher_id = b.teacher_id
            LEFT JOIN booking_reminders br_s
                ON br_s.booking_id = b.id
                AND br_s.reminder_window = $1
                AND br_s.recipient = 'student'
            LEFT JOIN booking_reminders br_t
                ON br_t.booking_id = b.id
                AND br_t.reminder_window = $1
                AND br_t.recipient = 'teacher'
            WHERE b.is_deleted = FALSE
              AND b.booking_status = 'confirmed'
              AND (b.booking_date + b.start_time) BETWEEN $2 AND $3
        """
        rows = await supabase_service.pool.fetch(sql, window_label, lo, hi)

        sent = 0
        failed = 0
        for row in rows:
            d = dict(row)
            booking_id = str(d["booking_id"])
            booking_data = {
                "id": booking_id,
                "booking_date": str(d["booking_date"]),
                "start_time": str(d["start_time"]),
                "course_name": d["course_name"],
                "teacher_name": d["teacher_name"],
            }

            # 比照 lesson_note_reminder_service：先 mark 再推。
            # send_booking_reminder() 失敗時不重試（避免 cron 反覆 spam log）。
            if not d["student_sent"] and d.get("student_user_id"):
                await self._mark_sent(booking_id, window_label, "student")
                if await self._send(
                    str(d["student_user_id"]),
                    booking_data,
                    "student",
                    hours_before,
                ):
                    sent += 1
                else:
                    failed += 1

            if not d["teacher_sent"] and d.get("teacher_user_id"):
                await self._mark_sent(booking_id, window_label, "teacher")
                if await self._send(
                    str(d["teacher_user_id"]),
                    booking_data,
                    "teacher",
                    hours_before,
                ):
                    sent += 1
                else:
                    failed += 1

        return {"sent": sent, "failed": failed}

    async def _send(
        self,
        user_id: str,
        booking_data: dict,
        channel_type: str,
        hours_before: int,
    ) -> bool:
        try:
            return await line_message_service.send_booking_reminder(
                user_id=user_id,
                booking_data=booking_data,
                channel_type=channel_type,
                hours_before=hours_before,
            )
        except Exception as e:
            logger.warning(
                f"send_booking_reminder 失敗 user={user_id} channel={channel_type}: {e}"
            )
            return False

    async def _mark_sent(
        self, booking_id: str, window_label: str, recipient: str
    ) -> None:
        sql = """
            INSERT INTO booking_reminders (booking_id, reminder_window, recipient)
            VALUES ($1, $2, $3)
            ON CONFLICT (booking_id, reminder_window, recipient) DO NOTHING
        """
        await supabase_service.pool.execute(sql, booking_id, window_label, recipient)


booking_reminder_service = BookingReminderService()
