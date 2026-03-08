"""
Line Message 服務 - 發送 Line 推播通知
支援多頻道（學生/老師/員工使用不同 Channel）
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum

import httpx

from app.config import settings, ChannelType
from app.services.supabase_service import supabase_service
from app.services.line_binding_service import line_binding_service


class NotificationType(str, Enum):
    """通知類型"""
    BOOKING_CONFIRMATION = "booking_confirmation"
    BOOKING_REMINDER = "booking_reminder"
    BOOKING_CANCELLED = "booking_cancelled"
    STATUS_UPDATE = "status_update"
    GENERAL = "general"


class NotificationStatus(str, Enum):
    """通知狀態"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class LineMessageService:
    """Line Messaging API 服務（多頻道支援）"""

    # Line Messaging API 端點
    PUSH_URL = "https://api.line.me/v2/bot/message/push"
    MULTICAST_URL = "https://api.line.me/v2/bot/message/multicast"
    BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"

    def get_channel_token(self, channel_type: ChannelType) -> Optional[str]:
        """取得指定頻道的 Messaging Token"""
        channel = settings.get_line_channel(channel_type)
        return channel.messaging_token if channel.messaging_token else None

    def is_channel_configured(self, channel_type: ChannelType) -> bool:
        """檢查指定頻道的 Messaging API 是否已設定"""
        return bool(self.get_channel_token(channel_type))

    @property
    def is_configured(self) -> bool:
        """檢查是否有任何頻道的 Messaging API 已設定"""
        return settings.line_messaging_enabled

    async def send_push_message(
        self,
        line_user_id: str,
        messages: List[Dict[str, Any]],
        channel_type: ChannelType
    ) -> Optional[str]:
        """
        發送推播訊息給單一用戶

        Args:
            line_user_id: Line 用戶 ID
            messages: 訊息列表
            channel_type: 頻道類型

        Returns:
            Line message ID，失敗則返回 None
        """
        channel_token = self.get_channel_token(channel_type)
        if not channel_token:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.PUSH_URL,
                json={
                    "to": line_user_id,
                    "messages": messages,
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {channel_token}",
                }
            )

            if response.status_code == 200:
                return response.headers.get("x-line-request-id")
            return None

    async def send_text_message(
        self,
        line_user_id: str,
        text: str,
        channel_type: ChannelType
    ) -> Optional[str]:
        """
        發送文字訊息

        Args:
            line_user_id: Line 用戶 ID
            text: 訊息文字
            channel_type: 頻道類型

        Returns:
            Line message ID
        """
        messages = [{"type": "text", "text": text}]
        return await self.send_push_message(line_user_id, messages, channel_type)

    async def send_booking_confirmation(
        self,
        user_id: str,
        booking_data: Dict[str, Any],
        channel_type: ChannelType
    ) -> bool:
        """
        發送預約確認通知

        Args:
            user_id: 用戶 ID
            booking_data: 預約資料
            channel_type: 頻道類型

        Returns:
            True 如果發送成功
        """
        # 檢查用戶是否有啟用此類通知
        binding = await line_binding_service.get_binding_by_user(user_id, channel_type)
        if not binding or binding.binding_status != "active":
            return False

        if not binding.notify_booking_confirmation:
            await self._log_notification(
                user_id=user_id,
                line_user_id=binding.line_user_id,
                channel_type=channel_type,
                notification_type=NotificationType.BOOKING_CONFIRMATION,
                status=NotificationStatus.SKIPPED,
                reference_id=booking_data.get("id"),
                reference_type="booking",
            )
            return False

        # 建立訊息
        message = self._build_booking_confirmation_message(booking_data)

        # 發送
        message_id = await self.send_push_message(
            binding.line_user_id,
            [message],
            channel_type
        )

        # 記錄
        await self._log_notification(
            user_id=user_id,
            line_user_id=binding.line_user_id,
            channel_type=channel_type,
            notification_type=NotificationType.BOOKING_CONFIRMATION,
            status=NotificationStatus.SENT if message_id else NotificationStatus.FAILED,
            reference_id=booking_data.get("id"),
            reference_type="booking",
            message_content=message.get("text") or message.get("altText"),
            line_message_id=message_id,
        )

        return message_id is not None

    async def send_booking_reminder(
        self,
        user_id: str,
        booking_data: Dict[str, Any],
        channel_type: ChannelType,
        hours_before: int = 24
    ) -> bool:
        """
        發送預約提醒通知

        Args:
            user_id: 用戶 ID
            booking_data: 預約資料
            channel_type: 頻道類型
            hours_before: 提前幾小時提醒

        Returns:
            True 如果發送成功
        """
        binding = await line_binding_service.get_binding_by_user(user_id, channel_type)
        if not binding or binding.binding_status != "active":
            return False

        if not binding.notify_booking_reminder:
            await self._log_notification(
                user_id=user_id,
                line_user_id=binding.line_user_id,
                channel_type=channel_type,
                notification_type=NotificationType.BOOKING_REMINDER,
                status=NotificationStatus.SKIPPED,
                reference_id=booking_data.get("id"),
                reference_type="booking",
            )
            return False

        message = self._build_booking_reminder_message(booking_data, hours_before)

        message_id = await self.send_push_message(
            binding.line_user_id,
            [message],
            channel_type
        )

        await self._log_notification(
            user_id=user_id,
            line_user_id=binding.line_user_id,
            channel_type=channel_type,
            notification_type=NotificationType.BOOKING_REMINDER,
            status=NotificationStatus.SENT if message_id else NotificationStatus.FAILED,
            reference_id=booking_data.get("id"),
            reference_type="booking",
            message_content=message.get("text") or message.get("altText"),
            line_message_id=message_id,
        )

        return message_id is not None

    async def send_status_update(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        old_status: str,
        new_status: str,
        channel_type: ChannelType,
        extra_info: Optional[Dict] = None
    ) -> bool:
        """
        發送狀態更新通知

        Args:
            user_id: 用戶 ID
            entity_type: 實體類型（如 booking, leave_record）
            entity_id: 實體 ID
            old_status: 舊狀態
            new_status: 新狀態
            channel_type: 頻道類型
            extra_info: 額外資訊

        Returns:
            True 如果發送成功
        """
        binding = await line_binding_service.get_binding_by_user(user_id, channel_type)
        if not binding or binding.binding_status != "active":
            return False

        if not binding.notify_status_update:
            await self._log_notification(
                user_id=user_id,
                line_user_id=binding.line_user_id,
                channel_type=channel_type,
                notification_type=NotificationType.STATUS_UPDATE,
                status=NotificationStatus.SKIPPED,
                reference_id=entity_id,
                reference_type=entity_type,
            )
            return False

        message = self._build_status_update_message(
            entity_type, old_status, new_status, extra_info
        )

        message_id = await self.send_push_message(
            binding.line_user_id,
            [message],
            channel_type
        )

        await self._log_notification(
            user_id=user_id,
            line_user_id=binding.line_user_id,
            channel_type=channel_type,
            notification_type=NotificationType.STATUS_UPDATE,
            status=NotificationStatus.SENT if message_id else NotificationStatus.FAILED,
            reference_id=entity_id,
            reference_type=entity_type,
            message_content=message.get("text") or message.get("altText"),
            line_message_id=message_id,
        )

        return message_id is not None

    async def send_custom_notification(
        self,
        user_id: str,
        message_text: str,
        channel_type: ChannelType,
        notification_type: NotificationType = NotificationType.GENERAL
    ) -> bool:
        """
        發送自訂通知

        Args:
            user_id: 用戶 ID
            message_text: 訊息內容
            channel_type: 頻道類型
            notification_type: 通知類型

        Returns:
            True 如果發送成功
        """
        binding = await line_binding_service.get_binding_by_user(user_id, channel_type)
        if not binding or binding.binding_status != "active":
            return False

        message_id = await self.send_text_message(
            binding.line_user_id,
            message_text,
            channel_type
        )

        await self._log_notification(
            user_id=user_id,
            line_user_id=binding.line_user_id,
            channel_type=channel_type,
            notification_type=notification_type,
            status=NotificationStatus.SENT if message_id else NotificationStatus.FAILED,
            message_content=message_text,
            line_message_id=message_id,
        )

        return message_id is not None

    def _build_booking_confirmation_message(
        self,
        booking_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """建立預約確認訊息"""
        booking_date = booking_data.get("booking_date", "")
        start_time = booking_data.get("start_time", "")
        course_name = booking_data.get("course_name", "課程")
        teacher_name = booking_data.get("teacher_name", "老師")

        text = (
            f"✅ 預約確認\n\n"
            f"課程：{course_name}\n"
            f"老師：{teacher_name}\n"
            f"日期：{booking_date}\n"
            f"時間：{start_time}\n\n"
            f"請準時上課！"
        )

        return {"type": "text", "text": text}

    def _build_booking_reminder_message(
        self,
        booking_data: Dict[str, Any],
        hours_before: int
    ) -> Dict[str, Any]:
        """建立預約提醒訊息"""
        booking_date = booking_data.get("booking_date", "")
        start_time = booking_data.get("start_time", "")
        course_name = booking_data.get("course_name", "課程")
        teacher_name = booking_data.get("teacher_name", "老師")

        text = (
            f"⏰ 課程提醒\n\n"
            f"您有一堂課程即將在 {hours_before} 小時後開始：\n\n"
            f"課程：{course_name}\n"
            f"老師：{teacher_name}\n"
            f"日期：{booking_date}\n"
            f"時間：{start_time}\n\n"
            f"請記得準時上課！"
        )

        return {"type": "text", "text": text}

    def _build_status_update_message(
        self,
        entity_type: str,
        old_status: str,
        new_status: str,
        extra_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """建立狀態更新訊息"""
        entity_names = {
            "booking": "預約",
            "leave_record": "請假",
            "contract": "合約",
        }

        status_names = {
            "pending": "待處理",
            "confirmed": "已確認",
            "approved": "已核准",
            "rejected": "已拒絕",
            "cancelled": "已取消",
            "completed": "已完成",
        }

        entity_name = entity_names.get(entity_type, entity_type)
        old_status_name = status_names.get(old_status, old_status)
        new_status_name = status_names.get(new_status, new_status)

        text = (
            f"📋 狀態更新\n\n"
            f"您的{entity_name}狀態已更新：\n"
            f"{old_status_name} → {new_status_name}"
        )

        if extra_info:
            if extra_info.get("reason"):
                text += f"\n\n原因：{extra_info['reason']}"

        return {"type": "text", "text": text}

    async def _log_notification(
        self,
        user_id: str,
        line_user_id: str,
        channel_type: ChannelType,
        notification_type: NotificationType,
        status: NotificationStatus,
        reference_id: Optional[str] = None,
        reference_type: Optional[str] = None,
        message_content: Optional[str] = None,
        line_message_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """記錄通知日誌"""
        try:
            data = {
                "user_id": user_id,
                "line_user_id": line_user_id,
                "channel_type": channel_type,
                "notification_type": notification_type.value,
                "notification_status": status.value,
                "reference_id": reference_id,
                "reference_type": reference_type,
                "message_content": message_content,
                "line_message_id": line_message_id,
                "error_message": error_message,
            }

            if status == NotificationStatus.SENT:
                data["sent_at"] = datetime.now(timezone.utc).isoformat()

            await supabase_service.table_insert(
                table="line_notification_logs",
                data=data,
            )
        except Exception:
            pass  # 記錄失敗不影響主流程


# 單例
line_message_service = LineMessageService()
