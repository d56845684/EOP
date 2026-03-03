"""
Zoom 服務 - 帳號池管理 + 會議建立 + Webhook 處理
支援 S2S OAuth 帳號池 + 教師 OAuth 自用帳號
"""
from typing import Optional, Dict, Any
from datetime import datetime, date, time, timezone, timedelta
import hashlib
import hmac
import base64
import logging
import json

import httpx

from app.config import settings
from app.services.supabase_service import supabase_service
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)

# Zoom API 端點
ZOOM_API_BASE = "https://api.zoom.us/v2"
ZOOM_OAUTH_TOKEN_URL = "https://zoom.us/oauth/token"
ZOOM_OAUTH_AUTHORIZE_URL = "https://zoom.us/oauth/authorize"


class ZoomService:
    """Zoom API 服務"""

    # ============================================
    # S2S OAuth Token（帳號池）
    # ============================================

    async def get_s2s_token(self, account: dict) -> Optional[str]:
        """
        取得 S2S OAuth token，Redis 快取 55 分鐘

        Args:
            account: zoom_accounts 表的記錄
        Returns:
            access_token 或 None
        """
        cache_key = f"zoom:s2s_token:{account['id']}"

        # 嘗試從 Redis 取得快取的 token
        try:
            cached = await redis_service.get(cache_key)
            if cached:
                return cached
        except Exception:
            pass

        # 向 Zoom 請求新 token
        try:
            credentials = base64.b64encode(
                f"{account['zoom_client_id']}:{account['zoom_client_secret']}".encode()
            ).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ZOOM_OAUTH_TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "account_credentials",
                        "account_id": account["zoom_account_id"],
                    },
                    timeout=10.0,
                )

            if response.status_code != 200:
                logger.error(f"Zoom S2S token 請求失敗: {response.status_code} {response.text}")
                return None

            data = response.json()
            token = data.get("access_token")
            if not token:
                return None

            # 快取 55 分鐘（token 有效期通常 60 分鐘）
            try:
                await redis_service.set(cache_key, token, expire_seconds=3300)
            except Exception:
                pass

            return token

        except Exception as e:
            logger.error(f"Zoom S2S token 取得失敗: {e}")
            return None

    # ============================================
    # 教師 OAuth Token
    # ============================================

    async def refresh_teacher_token(self, teacher_id: str) -> Optional[str]:
        """
        重新整理教師的 Zoom OAuth token

        Returns:
            新的 access_token 或 None
        """
        if not settings.zoom_oauth_configured:
            return None

        try:
            records = await supabase_service.table_select(
                table="teacher_zoom_accounts",
                select="zoom_refresh_token,zoom_token_expires_at",
                filters={"teacher_id": teacher_id, "is_deleted": "eq.false"},
                use_service_key=True,
            )
            if not records or not records[0].get("zoom_refresh_token"):
                return None

            refresh_token = records[0]["zoom_refresh_token"]

            credentials = base64.b64encode(
                f"{settings.ZOOM_OAUTH_CLIENT_ID}:{settings.ZOOM_OAUTH_CLIENT_SECRET}".encode()
            ).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ZOOM_OAUTH_TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                    timeout=10.0,
                )

            if response.status_code != 200:
                logger.error(f"教師 Zoom token refresh 失敗: {response.status_code}")
                return None

            data = response.json()
            new_access = data.get("access_token")
            new_refresh = data.get("refresh_token", refresh_token)
            expires_in = data.get("expires_in", 3600)

            # 更新 DB
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            await supabase_service.table_update(
                table="teacher_zoom_accounts",
                data={
                    "zoom_access_token": new_access,
                    "zoom_refresh_token": new_refresh,
                    "zoom_token_expires_at": expires_at.isoformat(),
                },
                filters={"teacher_id": teacher_id, "is_deleted": "eq.false"},
                use_service_key=True,
            )

            return new_access

        except Exception as e:
            logger.error(f"教師 Zoom token refresh 失敗: {e}")
            return None

    async def get_teacher_token(self, teacher_id: str) -> Optional[str]:
        """
        取得教師的 Zoom token，過期時自動 refresh
        """
        try:
            records = await supabase_service.table_select(
                table="teacher_zoom_accounts",
                select="zoom_access_token,zoom_refresh_token,zoom_token_expires_at",
                filters={"teacher_id": teacher_id, "is_deleted": "eq.false"},
                use_service_key=True,
            )
            if not records:
                return None

            record = records[0]
            if not record.get("zoom_access_token"):
                return None

            # 檢查是否過期（提前 5 分鐘）
            expires_at = record.get("zoom_token_expires_at")
            if expires_at:
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5):
                    return await self.refresh_teacher_token(teacher_id)

            return record["zoom_access_token"]

        except Exception as e:
            logger.error(f"取得教師 Zoom token 失敗: {e}")
            return None

    # ============================================
    # Zoom Meeting CRUD
    # ============================================

    async def create_meeting(
        self,
        token: str,
        topic: str,
        start_time: str,
        duration: int,
        user_id: str = "me",
    ) -> Optional[dict]:
        """
        透過 Zoom API 建立會議

        Args:
            token: Zoom access token
            topic: 會議主題
            start_time: ISO 8601 格式的開始時間
            duration: 會議時長（分鐘）
            user_id: Zoom user ID，預設 "me"

        Returns:
            Zoom API 回應 dict 或 None
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{ZOOM_API_BASE}/users/{user_id}/meetings",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "topic": topic,
                        "type": 2,  # scheduled meeting
                        "start_time": start_time,
                        "duration": duration,
                        "timezone": "Asia/Taipei",
                        "settings": {
                            "join_before_host": True,
                            "waiting_room": False,
                            "auto_recording": "cloud",
                            "mute_upon_entry": True,
                        },
                    },
                    timeout=15.0,
                )

            if response.status_code not in (200, 201):
                logger.error(f"Zoom 建立會議失敗: {response.status_code} {response.text}")
                return None

            return response.json()

        except Exception as e:
            logger.error(f"Zoom 建立會議異常: {e}")
            return None

    # ============================================
    # 帳號池分配邏輯
    # ============================================

    # ============================================
    # 主流程：為 Booking 建立會議
    # ============================================

    async def create_meeting_for_booking(
        self,
        booking_id: str,
        teacher_id: str,
        booking_date: date,
        start_time_val: time,
        end_time_val: time,
        topic: str = "",
    ) -> Optional[dict]:
        """
        為預約建立 Zoom 會議（主流程）

        優先順序：
        1. 教師有 Zoom OAuth 綁定 → 用教師帳號
        2. 教師 token 過期 → 嘗試 refresh
        3. Fallback 帳號池 → 找空閒帳號
        4. 無帳號可用 → log warning，不影響 booking

        Returns:
            zoom_meeting_logs 記錄 或 None
        """
        if not settings.zoom_enabled:
            return None

        # 檢查是否已有會議
        existing = await supabase_service.table_select(
            table="zoom_meeting_logs",
            select="id",
            filters={
                "booking_id": booking_id,
                "is_deleted": "eq.false",
                "meeting_status": "neq.cancelled",
            },
            use_service_key=True,
        )
        if existing:
            logger.info(f"Booking {booking_id} 已有 Zoom 會議")
            return existing[0]

        # 計算會議時長
        start_dt = datetime.combine(booking_date, start_time_val)
        end_dt = datetime.combine(booking_date, end_time_val)
        duration = int((end_dt - start_dt).total_seconds() / 60)
        if duration <= 0:
            duration = 60

        # 構建開始時間 ISO 格式
        start_iso = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        if not topic:
            topic = f"課程預約 {booking_date.strftime('%Y/%m/%d')} {start_time_val.strftime('%H:%M')}"

        token = None
        zoom_account_id = None
        used_teacher_account = False

        # 1. 嘗試教師自用帳號（僅課程時長 <= 30 分鐘時啟用）
        if duration <= 30:
            teacher_token = await self.get_teacher_token(teacher_id)
            if teacher_token:
                token = teacher_token
                used_teacher_account = True

        if token and used_teacher_account:
            # 教師自用帳號：直接建立
            result = await self._create_and_insert_meeting(
                token=token,
                booking_id=booking_id,
                teacher_id=teacher_id,
                zoom_account_id=None,
                used_teacher_account=True,
                booking_date=booking_date,
                start_time_val=start_time_val,
                end_time_val=end_time_val,
                start_iso=start_iso,
                duration=duration,
                topic=topic,
            )
            if result:
                return result
            # 教師帳號失敗（含時段衝突），fallback 帳號池
            logger.info(f"Booking {booking_id}: 教師帳號失敗，嘗試帳號池")

        # 2. 帳號池：逐一嘗試，DB EXCLUSION constraint 防止重疊
        accounts = await self._get_available_accounts(booking_date, start_time_val, end_time_val)
        for account in accounts:
            pool_token = await self.get_s2s_token(account)
            if not pool_token:
                continue

            result = await self._create_and_insert_meeting(
                token=pool_token,
                booking_id=booking_id,
                teacher_id=teacher_id,
                zoom_account_id=account["id"],
                used_teacher_account=False,
                booking_date=booking_date,
                start_time_val=start_time_val,
                end_time_val=end_time_val,
                start_iso=start_iso,
                duration=duration,
                topic=topic,
            )
            if result:
                return result
            # 此帳號衝突（race condition），嘗試下一個
            logger.info(f"Booking {booking_id}: 帳號 {account['id']} 時段衝突，嘗試下一個")

        logger.warning(f"Booking {booking_id}: 無可用 Zoom 帳號，跳過建立會議")
        return None

    async def _get_available_accounts(
        self, meeting_date: date, start_time_val: time, end_time_val: time
    ) -> list:
        """取得候選帳號列表（應用層預篩選，DB constraint 為最終保障）"""
        try:
            accounts = await supabase_service.table_select(
                table="zoom_accounts",
                select="*",
                filters={"is_active": "eq.true", "is_deleted": "eq.false"},
                use_service_key=True,
            )
            if not accounts:
                return []

            available = []
            for account in accounts:
                logs = await supabase_service.table_select(
                    table="zoom_meeting_logs",
                    select="id,start_time,end_time",
                    filters={
                        "zoom_account_id": account["id"],
                        "meeting_date": str(meeting_date),
                        "is_deleted": "eq.false",
                        "meeting_status": "neq.cancelled",
                    },
                    use_service_key=True,
                )

                has_conflict = False
                for log in logs:
                    log_start = log["start_time"]
                    log_end = log["end_time"]
                    if isinstance(log_start, str):
                        log_start = time.fromisoformat(log_start)
                    if isinstance(log_end, str):
                        log_end = time.fromisoformat(log_end)
                    if start_time_val < log_end and end_time_val > log_start:
                        has_conflict = True
                        break

                if not has_conflict:
                    available.append(account)

            return available

        except Exception as e:
            logger.error(f"查詢可用 Zoom 帳號失敗: {e}")
            return []

    async def _create_and_insert_meeting(
        self,
        token: str,
        booking_id: str,
        teacher_id: str,
        zoom_account_id: Optional[str],
        used_teacher_account: bool,
        booking_date: date,
        start_time_val: time,
        end_time_val: time,
        start_iso: str,
        duration: int,
        topic: str,
    ) -> Optional[dict]:
        """
        建立 Zoom 會議 + INSERT zoom_meeting_logs。
        如果 DB EXCLUSION constraint 拒絕（時段重疊），回傳 None 讓呼叫方嘗試下一個帳號。
        """
        meeting = await self.create_meeting(
            token=token,
            topic=topic,
            start_time=start_iso,
            duration=duration,
        )

        if not meeting:
            return None

        log_data = {
            "booking_id": booking_id,
            "zoom_account_id": zoom_account_id,
            "teacher_id": teacher_id if used_teacher_account else None,
            "zoom_meeting_id": str(meeting.get("id", "")),
            "zoom_meeting_uuid": meeting.get("uuid", ""),
            "join_url": meeting.get("join_url", ""),
            "start_url": meeting.get("start_url", ""),
            "passcode": meeting.get("password", ""),
            "meeting_date": str(booking_date),
            "start_time": str(start_time_val),
            "end_time": str(end_time_val),
            "meeting_status": "scheduled",
        }

        try:
            result = await supabase_service.table_insert(
                table="zoom_meeting_logs",
                data=log_data,
                use_service_key=True,
            )

            # 同步更新 booking_details 的 zoom 欄位
            await self._update_booking_details(
                booking_id,
                join_url=meeting.get("join_url", ""),
                meeting_id=str(meeting.get("id", "")),
                passcode=meeting.get("password", ""),
            )

            # 更新帳號每日用量
            if zoom_account_id:
                await self._increment_daily_count(zoom_account_id)

            logger.info(f"Booking {booking_id}: Zoom 會議建立成功 (meeting_id={meeting.get('id')})")
            return result

        except Exception as e:
            error_msg = str(e)
            # DB EXCLUSION constraint 衝突 → 回傳 None 讓呼叫方嘗試下一個帳號
            if "excl_zoom_account_no_overlap" in error_msg or "excl_zoom_teacher_no_overlap" in error_msg or "conflicting key value" in error_msg:
                logger.warning(f"Booking {booking_id}: DB 時段衝突 constraint 觸發，嘗試下一個帳號")
                return None
            logger.error(f"Booking {booking_id}: 寫入 zoom_meeting_logs 失敗: {e}")
            return None

    async def _update_booking_details(
        self, booking_id: str, join_url: str, meeting_id: str, passcode: str
    ):
        """更新 booking_details 的 Zoom 相關欄位"""
        try:
            existing = await supabase_service.table_select(
                table="booking_details",
                select="id",
                filters={"booking_id": booking_id, "is_deleted": "eq.false"},
                use_service_key=True,
            )
            if existing:
                await supabase_service.table_update(
                    table="booking_details",
                    data={
                        "zoom_link": join_url,
                        "zoom_meeting_id": meeting_id,
                        "zoom_password": passcode,
                    },
                    filters={"booking_id": booking_id},
                    use_service_key=True,
                )
        except Exception as e:
            logger.error(f"更新 booking_details zoom 欄位失敗: {e}")

    async def _increment_daily_count(self, zoom_account_id: str):
        """遞增帳號每日用量"""
        try:
            account = await supabase_service.table_select(
                table="zoom_accounts",
                select="daily_meeting_count,daily_count_reset_at",
                filters={"id": zoom_account_id},
                use_service_key=True,
            )
            if account:
                today = date.today()
                reset_at = account[0].get("daily_count_reset_at")
                if isinstance(reset_at, str):
                    reset_at = date.fromisoformat(reset_at)
                current_count = account[0].get("daily_meeting_count", 0)
                if reset_at and reset_at < today:
                    current_count = 0
                await supabase_service.table_update(
                    table="zoom_accounts",
                    data={
                        "daily_meeting_count": current_count + 1,
                        "daily_count_reset_at": str(today),
                    },
                    filters={"id": zoom_account_id},
                    use_service_key=True,
                )
        except Exception as e:
            logger.error(f"更新 Zoom 帳號每日用量失敗: {e}")

    # ============================================
    # Webhook 處理
    # ============================================

    def verify_webhook(self, body: bytes, timestamp: str, signature: str) -> bool:
        """
        驗證 Zoom Webhook 簽名 (HMAC-SHA256)
        """
        secret = settings.ZOOM_WEBHOOK_SECRET_TOKEN
        if not secret:
            logger.warning("ZOOM_WEBHOOK_SECRET_TOKEN 未設定，跳過驗證")
            return True

        message = f"v0:{timestamp}:{body.decode('utf-8')}"
        expected = "v0=" + hmac.new(
            secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    async def handle_recording_completed(self, payload: dict) -> bool:
        """
        處理 recording.completed webhook
        寫入錄影 URL 到 zoom_meeting_logs
        """
        try:
            meeting_obj = payload.get("object", {})
            meeting_id = str(meeting_obj.get("id", ""))
            meeting_uuid = meeting_obj.get("uuid", "")

            if not meeting_id:
                logger.warning("recording.completed: 缺少 meeting_id")
                return False

            # 取得錄影檔案資訊
            recording_files = meeting_obj.get("recording_files", [])
            # 優先取 MP4 共用檔案
            video_file = None
            for f in recording_files:
                if f.get("file_type") == "MP4" and f.get("recording_type") == "shared_screen_with_speaker_view":
                    video_file = f
                    break
            if not video_file and recording_files:
                for f in recording_files:
                    if f.get("file_type") == "MP4":
                        video_file = f
                        break
            if not video_file and recording_files:
                video_file = recording_files[0]

            update_data: dict = {
                "recording_completed_at": datetime.now(timezone.utc).isoformat(),
            }

            if video_file:
                update_data["recording_url"] = video_file.get("play_url", "")
                update_data["recording_download_url"] = video_file.get("download_url", "")
                update_data["recording_file_type"] = video_file.get("file_type", "")
                update_data["recording_file_size_bytes"] = video_file.get("file_size", 0)
                recording_start = video_file.get("recording_start", "")
                recording_end = video_file.get("recording_end", "")
                if recording_start and recording_end:
                    try:
                        start_dt = datetime.fromisoformat(recording_start.replace("Z", "+00:00"))
                        end_dt = datetime.fromisoformat(recording_end.replace("Z", "+00:00"))
                        update_data["recording_duration_seconds"] = int((end_dt - start_dt).total_seconds())
                    except Exception:
                        pass

            # 更新 zoom_meeting_logs
            result = await supabase_service.table_update(
                table="zoom_meeting_logs",
                data=update_data,
                filters={"zoom_meeting_id": meeting_id, "is_deleted": "eq.false"},
                use_service_key=True,
            )

            # 同步更新 booking_details
            if result and video_file:
                logs = await supabase_service.table_select(
                    table="zoom_meeting_logs",
                    select="booking_id",
                    filters={"zoom_meeting_id": meeting_id, "is_deleted": "eq.false"},
                    use_service_key=True,
                )
                if logs:
                    booking_id = logs[0]["booking_id"]
                    try:
                        await supabase_service.table_update(
                            table="booking_details",
                            data={
                                "recording_url": video_file.get("play_url", ""),
                                "recording_duration_seconds": update_data.get("recording_duration_seconds"),
                            },
                            filters={"booking_id": booking_id},
                            use_service_key=True,
                        )
                    except Exception:
                        pass

            logger.info(f"recording.completed 處理完成: meeting_id={meeting_id}")
            return True

        except Exception as e:
            logger.error(f"recording.completed 處理失敗: {e}")
            return False

    async def handle_meeting_ended(self, payload: dict) -> bool:
        """
        處理 meeting.ended webhook
        更新 meeting_status 為 ended
        """
        try:
            meeting_obj = payload.get("object", {})
            meeting_id = str(meeting_obj.get("id", ""))

            if not meeting_id:
                return False

            await supabase_service.table_update(
                table="zoom_meeting_logs",
                data={"meeting_status": "ended"},
                filters={"zoom_meeting_id": meeting_id, "is_deleted": "eq.false"},
                use_service_key=True,
            )

            logger.info(f"meeting.ended 處理完成: meeting_id={meeting_id}")
            return True

        except Exception as e:
            logger.error(f"meeting.ended 處理失敗: {e}")
            return False

    async def handle_meeting_started(self, payload: dict) -> bool:
        """
        處理 meeting.started webhook
        更新 meeting_status 為 started
        """
        try:
            meeting_obj = payload.get("object", {})
            meeting_id = str(meeting_obj.get("id", ""))

            if not meeting_id:
                return False

            await supabase_service.table_update(
                table="zoom_meeting_logs",
                data={"meeting_status": "started"},
                filters={"zoom_meeting_id": meeting_id, "is_deleted": "eq.false"},
                use_service_key=True,
            )

            logger.info(f"meeting.started 處理完成: meeting_id={meeting_id}")
            return True

        except Exception as e:
            logger.error(f"meeting.started 處理失敗: {e}")
            return False

    # ============================================
    # 教師 OAuth 流程
    # ============================================

    def get_oauth_authorize_url(self, state: str = "") -> str:
        """產生 Zoom OAuth 授權 URL"""
        params = {
            "response_type": "code",
            "client_id": settings.ZOOM_OAUTH_CLIENT_ID,
            "redirect_uri": settings.ZOOM_OAUTH_REDIRECT_URI,
        }
        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{ZOOM_OAUTH_AUTHORIZE_URL}?{query}"

    async def exchange_code_for_token(self, code: str) -> Optional[dict]:
        """
        用 authorization code 換取 token

        Returns:
            {"access_token", "refresh_token", "expires_in", ...} 或 None
        """
        try:
            credentials = base64.b64encode(
                f"{settings.ZOOM_OAUTH_CLIENT_ID}:{settings.ZOOM_OAUTH_CLIENT_SECRET}".encode()
            ).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ZOOM_OAUTH_TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": settings.ZOOM_OAUTH_REDIRECT_URI,
                    },
                    timeout=10.0,
                )

            if response.status_code != 200:
                logger.error(f"Zoom OAuth token exchange 失敗: {response.status_code} {response.text}")
                return None

            return response.json()

        except Exception as e:
            logger.error(f"Zoom OAuth token exchange 異常: {e}")
            return None

    async def get_zoom_user_info(self, access_token: str) -> Optional[dict]:
        """取得 Zoom 使用者資訊"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{ZOOM_API_BASE}/users/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )

            if response.status_code != 200:
                return None

            return response.json()

        except Exception as e:
            logger.error(f"取得 Zoom 使用者資訊失敗: {e}")
            return None

    async def cancel_meeting_for_booking(self, booking_id: str) -> bool:
        """取消 booking 的 Zoom 會議（更新 meeting_status）"""
        try:
            await supabase_service.table_update(
                table="zoom_meeting_logs",
                data={"meeting_status": "cancelled"},
                filters={
                    "booking_id": booking_id,
                    "is_deleted": "eq.false",
                    "meeting_status": "scheduled",
                },
                use_service_key=True,
            )
            logger.info(f"Booking {booking_id}: Zoom 會議已取消")
            return True
        except Exception as e:
            logger.error(f"取消 Zoom 會議失敗: {e}")
            return False


# Module-level singleton
zoom_service = ZoomService()
