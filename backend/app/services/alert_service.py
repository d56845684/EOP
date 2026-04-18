"""
System Alert Service — 寫入系統告警供管理員 dashboard 查看
"""
import logging
from typing import Optional
from app.services.supabase_service import supabase_service

logger = logging.getLogger(__name__)


class AlertService:

    async def create(
        self,
        alert_type: str,
        title: str,
        message: Optional[str] = None,
        severity: str = "error",
        metadata: Optional[dict] = None,
    ) -> None:
        """寫入一筆系統告警（fire-and-forget，失敗只 log 不拋錯）"""
        try:
            await supabase_service.table_insert(
                table="system_alerts",
                data={
                    "alert_type": alert_type,
                    "severity": severity,
                    "title": title,
                    "message": message,
                    "metadata": metadata or {},
                },
            )
        except Exception as e:
            logger.error(f"寫入系統告警失敗: {e}")


alert_service = AlertService()
