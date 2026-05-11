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

        帳號選擇規則：
        - 時長 < 40 分鐘 → 優先 basic，無可用則 fallback pro/business
        - 時長 >= 40 分鐘 → 只用 pro / business 帳號
        - 無帳號可用 → log warning，不影響 booking

        Returns:
            zoom_meeting_logs 記錄 或 None
        """
        if not settings.zoom_enabled:
            return None

        # 檢查是否為過去時間，不允許建立過去的會議
        now = datetime.now()
        booking_start = datetime.combine(booking_date, start_time_val)
        if booking_start < now:
            logger.warning(f"Booking {booking_id}: 無法建立過去的 Zoom 會議 ({booking_start})")
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
            # 查詢預約相關的學生/教師/課程名稱
            booking_info = await supabase_service.pool.fetchrow(
                """SELECT b.booking_no, s.name AS student_name,
                          s.eng_name AS student_eng_name,
                          t.name AS teacher_name, c.course_name
                   FROM bookings b
                   LEFT JOIN students s ON s.id = b.student_id
                   LEFT JOIN teachers t ON t.id = b.teacher_id
                   LEFT JOIN courses c ON c.id = b.course_id
                   WHERE b.id = $1""",
                __import__('uuid').UUID(booking_id),
            )
            if not booking_info:
                logger.error(f"Booking {booking_id}: 查無預約資料，無法建立 Zoom 會議")
                return None

            parts = [f"[{booking_info['booking_no'] or booking_id[:8]}]"]
            if booking_info["course_name"]:
                parts.append(booking_info["course_name"])
            if booking_info["student_name"]:
                student_display = booking_info["student_name"]
                if booking_info.get("student_eng_name"):
                    student_display += f"({booking_info['student_eng_name']})"
                parts.append(student_display)
            if booking_info["teacher_name"]:
                parts.append(f"/ {booking_info['teacher_name']}")
            parts.append(f"{booking_date.strftime('%m/%d')} {start_time_val.strftime('%H:%M')}")
            topic = " ".join(parts)

        # 根據時長決定帳號等級優先順序：
        # < 40 分鐘 → 優先 basic，沒有才 fallback pro/business
        # >= 40 分鐘 → 只用 pro/business
        if duration < 40:
            tier_priority = [["basic"], ["pro", "business"]]
        else:
            tier_priority = [["pro", "business"]]

        # 帳號池：依 tier 優先順序逐一嘗試，DB EXCLUSION constraint 防止重疊
        for tiers in tier_priority:
            accounts = await self._get_available_accounts(booking_date, start_time_val, end_time_val, tiers)
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
                logger.info(f"Booking {booking_id}: 帳號 {account['id']} 時段衝突，嘗試下一個")

            if accounts:
                logger.info(f"Booking {booking_id}: {tiers} 帳號皆衝突，嘗試下一等級")

        logger.warning(f"Booking {booking_id}: 無可用 Zoom 帳號，跳過建立會議")
        return None

    async def _get_available_accounts(
        self, meeting_date: date, start_time_val: time, end_time_val: time,
        required_tiers: list[str] | None = None,
    ) -> list:
        """
        一條 SQL 查出在指定時段無衝突的空閒帳號。
        用 LEFT JOIN + 時段重疊過濾，避免 N+1 查詢。
        DB EXCLUSION constraint 仍為最終保障。

        required_tiers: 限定帳號等級，例如 ['basic'] 或 ['pro', 'business']
        """
        try:
            tier_clause = ""
            params: list = [meeting_date, start_time_val, end_time_val]
            if required_tiers:
                placeholders = ", ".join(f"${i}" for i in range(4, 4 + len(required_tiers)))
                tier_clause = f"AND a.account_tier IN ({placeholders})"
                params.extend(required_tiers)

            sql = f"""
                SELECT a.*
                FROM zoom_accounts a
                LEFT JOIN zoom_meeting_logs l
                    ON l.zoom_account_id = a.id
                    AND l.meeting_date = $1
                    AND l.is_deleted = FALSE
                    AND l.meeting_status != 'cancelled'
                    AND l.start_time < $3
                    AND l.end_time > $2
                WHERE a.is_active = TRUE
                    AND a.is_deleted = FALSE
                    {tier_clause}
                    AND l.id IS NULL
                ORDER BY a.daily_meeting_count ASC
            """
            rows = await supabase_service.pool.fetch(sql, *params)
            return [dict(r) for r in rows]

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

    async def _increment_daily_count(self, zoom_account_id: str):
        """遞增帳號每日用量"""
        try:
            account = await supabase_service.table_select(
                table="zoom_accounts",
                select="daily_meeting_count,daily_count_reset_at",
                filters={"id": zoom_account_id},
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
                filters={"zoom_meeting_id": f"text.{meeting_id}", "is_deleted": "is.false"},
            )

            logger.info(f"recording.completed 處理完成: meeting_id={meeting_id}")

            # 發送 SQS 任務：將錄影轉移至 Google Drive
            if settings.SQS_QUEUE_URL and video_file:
                await self._enqueue_recording_transfer(meeting_id, video_file)

            return True

        except Exception as e:
            logger.error(f"recording.completed 處理失敗: {e}")
            return False

    async def fetch_meeting_recording(self, booking_id: str) -> Optional[dict]:
        """
        手動呼叫 Zoom API 取得會議錄影資訊

        用於 webhook 漏掉或延遲時，主動抓取錄影 URL。
        """
        try:
            # 1. 取得該 booking 的 zoom meeting log
            meeting_logs = await supabase_service.table_select(
                table="zoom_meeting_logs",
                select="id,zoom_meeting_id,zoom_account_id,teacher_id,recording_url",
                filters={"booking_id": f"eq.{booking_id}", "is_deleted": "eq.false"},
            )
            if not meeting_logs:
                logger.warning(f"fetch_recording: booking {booking_id} 無 Zoom 會議紀錄")
                return None

            log = meeting_logs[0]
            zoom_meeting_id = log.get("zoom_meeting_id")
            if not zoom_meeting_id:
                return None

            # 2. 取得 access token（帳號池 S2S 優先）
            token = None
            zoom_account_id = log.get("zoom_account_id")
            if zoom_account_id:
                accounts = await supabase_service.table_select(
                    table="zoom_accounts",
                    select="id,zoom_account_id,zoom_client_id,zoom_client_secret",
                    filters={"id": zoom_account_id},
                )
                if accounts:
                    token = await self.get_s2s_token(accounts[0])

            if not token and log.get("teacher_id"):
                token = await self.refresh_teacher_token(str(log["teacher_id"]))

            if not token:
                logger.error(f"fetch_recording: 無法取得 Zoom token (booking={booking_id})")
                return None

            # 3. 呼叫 Zoom API 取得錄影
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{ZOOM_API_BASE}/meetings/{zoom_meeting_id}/recordings",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=15.0,
                )

            if response.status_code == 404:
                logger.info(f"fetch_recording: 會議 {zoom_meeting_id} 尚無錄影")
                return None

            if response.status_code != 200:
                logger.error(f"fetch_recording: Zoom API 回傳 {response.status_code}: {response.text[:200]}")
                return None

            data = response.json()
            recording_files = data.get("recording_files", [])

            # 4. 選取最佳錄影檔（複用 webhook 邏輯）
            video_file = None
            for f in recording_files:
                if f.get("file_type") == "MP4" and f.get("recording_type") == "shared_screen_with_speaker_view":
                    video_file = f
                    break
            if not video_file:
                for f in recording_files:
                    if f.get("file_type") == "MP4":
                        video_file = f
                        break
            if not video_file and recording_files:
                video_file = recording_files[0]

            if not video_file:
                logger.info(f"fetch_recording: 會議 {zoom_meeting_id} 無可用錄影檔案")
                return None

            # 5. 更新 DB
            update_data = {
                "recording_url": video_file.get("play_url", ""),
                "recording_download_url": video_file.get("download_url", ""),
                "recording_file_type": video_file.get("file_type", ""),
                "recording_file_size_bytes": video_file.get("file_size", 0),
                "recording_completed_at": datetime.now(timezone.utc).isoformat(),
            }
            recording_start = video_file.get("recording_start", "")
            recording_end = video_file.get("recording_end", "")
            if recording_start and recording_end:
                try:
                    start_dt = datetime.fromisoformat(recording_start.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(recording_end.replace("Z", "+00:00"))
                    update_data["recording_duration_seconds"] = int((end_dt - start_dt).total_seconds())
                except Exception:
                    pass

            result = await supabase_service.table_update(
                table="zoom_meeting_logs",
                data=update_data,
                filters={"id": log["id"]},
            )

            logger.info(f"fetch_recording: 成功取得錄影 meeting={zoom_meeting_id}, url={video_file.get('play_url', '')[:60]}")

            # 6. 觸發 Google Drive 轉存
            if settings.SQS_QUEUE_URL and video_file.get("download_url"):
                await self._enqueue_recording_transfer(zoom_meeting_id, video_file)

            return result if result else None

        except Exception as e:
            logger.error(f"fetch_recording 失敗: {e}")
            return None

    async def _enqueue_recording_transfer(self, meeting_id: str, video_file: dict):
        """查詢老師/學生 email，發送 SQS 錄影轉移任務"""
        try:
            from app.services.sqs_service import sqs_service

            # 從 zoom_meeting_logs 取 booking_id, teacher_id, zoom_account_id
            log_rows = await supabase_service.table_select(
                table="zoom_meeting_logs",
                select="booking_id,teacher_id,zoom_account_id",
                filters={"zoom_meeting_id": f"text.{meeting_id}", "is_deleted": "is.false"},
            )
            teacher_email, student_email = None, None
            if log_rows:
                log = log_rows[0]
                # teacher email
                if log.get("teacher_id"):
                    t = await supabase_service.table_select(
                        table="teachers", select="email",
                        filters={"id": log["teacher_id"]},
                    )
                    if t:
                        teacher_email = t[0].get("email")
                # student email（透過 booking → student_id）
                if log.get("booking_id"):
                    b = await supabase_service.table_select(
                        table="bookings", select="student_id",
                        filters={"id": log["booking_id"]},
                    )
                    if b and b[0].get("student_id"):
                        s = await supabase_service.table_select(
                            table="students", select="email",
                            filters={"id": b[0]["student_id"]},
                        )
                        if s:
                            student_email = s[0].get("email")

            # 取 Zoom access token（供 Lambda 下載錄影用）
            token = await self._get_token_for_download(log_rows[0] if log_rows else {})

            share_emails = [e for e in [teacher_email, student_email] if e]

            # SQS 訊息不帶 Zoom 憑證（Lambda 自己從環境變數取得）
            sqs_service.send_message({
                "meeting_id": meeting_id,
                "file_type": video_file.get("file_type", "MP4"),
                "file_size": video_file.get("file_size", 0),
                "share_emails": share_emails,
                "callback_url": f"{settings.BACKEND_BASE_URL}/api/v1/zoom/recording-callback",
                "callback_secret": settings.RECORDING_CALLBACK_SECRET,
            })

            await supabase_service.table_update(
                table="zoom_meeting_logs",
                data={"recording_transfer_status": "queued"},
                filters={"zoom_meeting_id": f"text.{meeting_id}", "is_deleted": "is.false"},
            )

            logger.info(f"錄影轉移任務已發送 SQS: meeting_id={meeting_id}, share_emails={share_emails}")

        except Exception as e:
            logger.error(f"SQS 發送失敗: {e}")

    async def _get_token_for_download(self, log: dict) -> Optional[str]:
        """根據 meeting log 取得 Zoom token 供錄影下載"""
        if log.get("zoom_account_id"):
            accounts = await supabase_service.table_select(
                table="zoom_accounts",
                select="*",
                filters={"id": log["zoom_account_id"], "is_deleted": "eq.false"},
            )
            if accounts:
                return await self.get_s2s_token(accounts[0])
        if log.get("teacher_id"):
            return await self.get_teacher_token(log["teacher_id"])
        return None

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
                filters={"zoom_meeting_id": f"text.{meeting_id}", "is_deleted": "is.false"},
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
                filters={"zoom_meeting_id": f"text.{meeting_id}", "is_deleted": "is.false"},
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

    async def end_meeting(self, token: str, meeting_id: str) -> bool:
        """透過 Zoom API 結束進行中的會議"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{ZOOM_API_BASE}/meetings/{meeting_id}/status",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"action": "end"},
                    timeout=10.0,
                )
            # 204=成功, 404=會議不存在或已結束
            if response.status_code in (204, 404):
                return True
            logger.error(f"Zoom 結束會議失敗: {response.status_code} {response.text}")
            return False
        except Exception as e:
            logger.error(f"Zoom 結束會議異常: {e}")
            return False

    async def _get_token_for_log(self, log: dict) -> Optional[str]:
        """根據 meeting log 取得對應的 Zoom token（帳號池或教師 OAuth）"""
        if log.get("zoom_account_id"):
            accounts = await supabase_service.table_select(
                table="zoom_accounts",
                select="*",
                filters={"id": log["zoom_account_id"], "is_deleted": "eq.false"},
            )
            if accounts:
                return await self.get_s2s_token(accounts[0])
        elif log.get("teacher_id"):
            return await self.get_teacher_token(log["teacher_id"])
        return None

    async def auto_end_overdue_meetings(self) -> int:
        """
        自動結束超過預定時間的會議。
        查詢 meeting_status = 'started' 且 meeting_date + end_time < now 的會議，
        呼叫 Zoom API 結束 → 雲端錄影會自動觸發 recording.completed webhook。
        回傳結束的會議數量。
        """
        try:
            now = datetime.now()
            today = now.date()
            current_time = now.time()

            # 查出所有已開始但超過結束時間的會議
            sql = """
                SELECT id, zoom_meeting_id, zoom_account_id, teacher_id, booking_id
                FROM zoom_meeting_logs
                WHERE meeting_status = 'started'
                  AND is_deleted = FALSE
                  AND (
                      meeting_date < $1
                      OR (meeting_date = $1 AND end_time <= $2)
                  )
            """
            rows = await supabase_service.pool.fetch(sql, today, current_time)

            ended_count = 0
            for row in rows:
                log = dict(row)
                zoom_meeting_id = log.get("zoom_meeting_id")
                if not zoom_meeting_id:
                    continue

                token = await self._get_token_for_log(log)
                if not token:
                    logger.warning(f"auto_end: 無法取得 token 結束會議 {zoom_meeting_id}")
                    continue

                success = await self.end_meeting(token, zoom_meeting_id)
                if success:
                    ended_count += 1
                    logger.info(f"auto_end: 已結束超時會議 {zoom_meeting_id} (booking={log.get('booking_id')})")

            if ended_count > 0:
                logger.info(f"auto_end: 本次共結束 {ended_count} 場超時會議")
            return ended_count

        except Exception as e:
            logger.error(f"auto_end_overdue_meetings 失敗: {e}")
            return 0

    async def delete_zoom_meeting(self, token: str, meeting_id: str) -> bool:
        """透過 Zoom API 刪除會議"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{ZOOM_API_BASE}/meetings/{meeting_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
            # 204=成功刪除, 404=已不存在（都算成功）
            if response.status_code in (204, 404):
                return True
            logger.error(f"Zoom 刪除會議失敗: {response.status_code} {response.text}")
            return False
        except Exception as e:
            logger.error(f"Zoom 刪除會議異常: {e}")
            return False

    async def cancel_meeting_for_booking(self, booking_id: str) -> bool:
        """取消 booking 的 Zoom 會議（Zoom API 刪除 + DB 狀態更新）"""
        try:
            # 查出該 booking 的 scheduled 會議
            logs = await supabase_service.table_select(
                table="zoom_meeting_logs",
                select="id,zoom_meeting_id,zoom_account_id,teacher_id",
                filters={
                    "booking_id": booking_id,
                    "is_deleted": "eq.false",
                    "meeting_status": "scheduled",
                },
            )

            for log in (logs or []):
                zoom_meeting_id = log.get("zoom_meeting_id")
                if zoom_meeting_id:
                    token = await self._get_token_for_log(log)
                    if token:
                        await self.delete_zoom_meeting(token, zoom_meeting_id)
                    else:
                        logger.warning(f"Booking {booking_id}: 無法取得 token 刪除 Zoom 會議 {zoom_meeting_id}")

            # 更新 DB 狀態
            await supabase_service.table_update(
                table="zoom_meeting_logs",
                data={"meeting_status": "cancelled"},
                filters={
                    "booking_id": booking_id,
                    "is_deleted": "eq.false",
                    "meeting_status": "scheduled",
                },
            )

            logger.info(f"Booking {booking_id}: Zoom 會議已取消")
            return True
        except Exception as e:
            logger.error(f"取消 Zoom 會議失敗: {e}")
            return False

    async def delete_meeting_for_booking(self, booking_id: str) -> bool:
        """刪除 booking 對應的 Zoom 會議（不限 meeting_status）。

        與 cancel_meeting_for_booking 差別：cancel 僅處理 scheduled 狀態的會議
        （用於 booking 取消/退回），此方法處理所有非 cancelled 的 log
        （用於 booking completed 後清理 + 過期 sweep）。
        """
        try:
            logs = await supabase_service.table_select(
                table="zoom_meeting_logs",
                select="id,zoom_meeting_id,zoom_account_id,teacher_id",
                filters={
                    "booking_id": booking_id,
                    "is_deleted": "eq.false",
                    "meeting_status": "neq.cancelled",
                },
            )

            for log in (logs or []):
                zoom_meeting_id = log.get("zoom_meeting_id")
                if zoom_meeting_id:
                    token = await self._get_token_for_log(log)
                    if token:
                        await self.delete_zoom_meeting(token, zoom_meeting_id)
                    else:
                        logger.warning(f"Booking {booking_id}: 無法取得 token 刪除 Zoom 會議 {zoom_meeting_id}")

            await supabase_service.table_update(
                table="zoom_meeting_logs",
                data={"meeting_status": "cancelled"},
                filters={
                    "booking_id": booking_id,
                    "is_deleted": "eq.false",
                    "meeting_status": "neq.cancelled",
                },
            )

            logger.info(f"Booking {booking_id}: Zoom 會議已清理（completed/sweep）")
            return True
        except Exception as e:
            logger.error(f"清理 Zoom 會議失敗: {e}")
            return False

    async def auto_delete_stale_meetings(self, days: int = 14) -> int:
        """過期會議 sweep：刪除 N 天前已結束、但未被清理的 Zoom 會議。

        篩選條件：
        - zoom_meeting_logs.is_deleted = false
        - meeting_status != 'cancelled'
        - zoom_meeting_id 不為空
        - 對應 booking 的 booking_status != 'cancelled'（取消的由 cancel 流程處理）
        - meeting_date + end_time < NOW() - N days
        """
        try:
            cutoff_dt = datetime.now() - timedelta(days=days)
            cutoff_date = cutoff_dt.date()
            cutoff_time = cutoff_dt.time()

            sql = """
                SELECT zml.id, zml.zoom_meeting_id, zml.zoom_account_id,
                       zml.teacher_id, zml.booking_id
                FROM zoom_meeting_logs zml
                JOIN bookings b ON b.id = zml.booking_id
                WHERE zml.is_deleted = FALSE
                  AND zml.meeting_status <> 'cancelled'
                  AND zml.zoom_meeting_id IS NOT NULL
                  AND b.booking_status <> 'cancelled'
                  AND (
                      zml.meeting_date < $1
                      OR (zml.meeting_date = $1 AND zml.end_time <= $2)
                  )
            """
            rows = await supabase_service.pool.fetch(sql, cutoff_date, cutoff_time)

            deleted_count = 0
            for row in rows:
                log = dict(row)
                zoom_meeting_id = log.get("zoom_meeting_id")
                if not zoom_meeting_id:
                    continue

                token = await self._get_token_for_log(log)
                if not token:
                    logger.warning(f"sweep: 無法取得 token 刪除過期會議 {zoom_meeting_id}")
                    continue

                success = await self.delete_zoom_meeting(token, zoom_meeting_id)
                if success:
                    await supabase_service.table_update(
                        table="zoom_meeting_logs",
                        data={"meeting_status": "cancelled"},
                        filters={"id": log["id"]},
                    )
                    deleted_count += 1
                    logger.info(
                        f"sweep: 已刪除過期會議 {zoom_meeting_id} "
                        f"(booking={log.get('booking_id')})"
                    )

            if deleted_count > 0:
                logger.info(f"sweep: 本次共刪除 {deleted_count} 場過期會議")
            return deleted_count

        except Exception as e:
            logger.error(f"auto_delete_stale_meetings 失敗: {e}")
            return 0


# Module-level singleton
zoom_service = ZoomService()
