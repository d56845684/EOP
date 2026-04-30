"""
Google Service — OAuth token 管理 + Drive 設定 + Calendar 事件同步

管理員做一次 OAuth 授權（scope 含 Drive + Calendar），系統存 refresh token。
- Drive: Lambda 透過 internal API 取得 access token 上傳錄影
- Calendar: 預約建立/更新/刪除時同步到 Gmail 用戶的 Google Calendar
"""
import httpx
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from app.config import settings
from app.services.supabase_service import supabase_service

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_OAUTH_SCOPE = "https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/calendar openid email profile"
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
CALENDAR_TIMEZONE = "Asia/Taipei"


class GoogleService:

    # ============================================================
    # OAuth Token 管理
    # ============================================================

    def get_oauth_authorize_url(self, state: str = "") -> str:
        """產生 Google OAuth 授權 URL"""
        params = {
            "client_id": settings.GOOGLE_DRIVE_OAUTH_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_DRIVE_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": GOOGLE_OAUTH_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state
        return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Optional[dict]:
        """用 authorization code 換取 token"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "client_id": settings.GOOGLE_DRIVE_OAUTH_CLIENT_ID,
                        "client_secret": settings.GOOGLE_DRIVE_OAUTH_CLIENT_SECRET,
                        "code": code,
                        "grant_type": "authorization_code",
                        "redirect_uri": settings.GOOGLE_DRIVE_OAUTH_REDIRECT_URI,
                    },
                    timeout=10.0,
                )
            if resp.status_code != 200:
                logger.error(f"Google token exchange 失敗: {resp.status_code} {resp.text[:200]}")
                return None
            return resp.json()
        except Exception as e:
            logger.error(f"Google token exchange 例外: {e}")
            return None

    async def get_user_info(self, access_token: str) -> Optional[dict]:
        """取得 Google 使用者資訊（email, id）"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )
            if resp.status_code != 200:
                return None
            return resp.json()
        except Exception:
            return None

    async def refresh_access_token(self) -> Optional[str]:
        """用 refresh_token 換新的 access_token"""
        config = await self._get_active_config()
        if not config or not config.get("google_refresh_token"):
            return None

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "client_id": settings.GOOGLE_DRIVE_OAUTH_CLIENT_ID,
                        "client_secret": settings.GOOGLE_DRIVE_OAUTH_CLIENT_SECRET,
                        "refresh_token": config["google_refresh_token"],
                        "grant_type": "refresh_token",
                    },
                    timeout=10.0,
                )
            if resp.status_code != 200:
                logger.error(f"Google token refresh 失敗: {resp.status_code} {resp.text[:200]}")
                return None

            data = resp.json()
            new_access = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            await supabase_service.table_update(
                table="google_drive_config",
                data={
                    "google_access_token": new_access,
                    "google_token_expires_at": expires_at.isoformat(),
                    "updated_at": "now()",
                },
                filters={"id": config["id"]},
            )

            logger.info(f"Google token refreshed, expires_at={expires_at.isoformat()}")
            return new_access

        except Exception as e:
            logger.error(f"Google token refresh 例外: {e}")
            return None

    async def get_active_token(self) -> Optional[str]:
        """取得可用的 access_token，過期自動 refresh"""
        config = await self._get_active_config()
        if not config:
            return None

        expires_at = config.get("google_token_expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5):
                return await self.refresh_access_token()

        return config.get("google_access_token")

    # ============================================================
    # Drive 設定
    # ============================================================

    async def get_drive_config(self) -> Optional[dict]:
        """取得完整 Drive 設定（mode, folder_id, email 等）"""
        return await self._get_active_config()

    # ============================================================
    # Calendar 事件
    # ============================================================

    def _build_calendar_event(
        self,
        summary: str,
        description: str,
        date: str,
        start_time: str,
        end_time: str,
        attendee_emails: list[str],
    ) -> dict:
        return {
            "summary": summary,
            "description": description,
            "start": {"dateTime": f"{date}T{start_time}", "timeZone": CALENDAR_TIMEZONE},
            "end": {"dateTime": f"{date}T{end_time}", "timeZone": CALENDAR_TIMEZONE},
            "attendees": [{"email": e} for e in attendee_emails],
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 30}],
            },
        }

    async def create_calendar_event(
        self,
        booking_id: str,
        summary: str,
        description: str,
        date: str,
        start_time: str,
        end_time: str,
        student_email: Optional[str],
        teacher_email: Optional[str],
    ) -> bool:
        """建立 Calendar 事件並邀請 Gmail 用戶"""
        token = await self.get_active_token()
        if not token:
            logger.warning("Google Calendar: 無可用 OAuth token，跳過同步")
            return False

        attendees = []
        email_role_map = {}
        if student_email:
            attendees.append(student_email)
            email_role_map[student_email] = "student"
        if teacher_email:
            attendees.append(teacher_email)
            email_role_map[teacher_email] = "teacher"

        if not attendees:
            logger.info(f"Booking {booking_id}: 無 attendee email，跳過 Calendar 同步")
            return False

        body = self._build_calendar_event(
            summary=summary, description=description,
            date=date, start_time=start_time, end_time=end_time,
            attendee_emails=attendees,
        )

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{CALENDAR_API_BASE}/calendars/primary/events",
                    params={"sendUpdates": "all"},
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=body, timeout=15.0,
                )

            if resp.status_code not in (200, 201):
                logger.error(f"Calendar create 失敗: {resp.status_code} {resp.text[:300]}")
                return False

            event_id = resp.json().get("id")
            if not event_id:
                return False

            for email in attendees:
                await supabase_service.table_insert(
                    table="booking_calendar_events",
                    data={
                        "booking_id": booking_id,
                        "calendar_event_id": event_id,
                        "attendee_email": email,
                        "attendee_role": email_role_map[email],
                        "sync_status": "synced",
                    },
                )

            logger.info(f"Booking {booking_id}: Calendar 事件建立成功 (event={event_id}, attendees={attendees})")
            return True

        except Exception as e:
            logger.error(f"Calendar create 例外: {e}")
            return False

    async def update_calendar_event(
        self,
        booking_id: str,
        summary: str,
        description: str,
        date: str,
        start_time: str,
        end_time: str,
        student_email: Optional[str],
        teacher_email: Optional[str],
    ) -> bool:
        """更新已同步的 Calendar 事件"""
        token = await self.get_active_token()
        if not token:
            return False

        records = await supabase_service.table_select(
            table="booking_calendar_events",
            select="calendar_event_id",
            filters={"booking_id": booking_id, "sync_status": "synced"},
        )
        if not records:
            return False

        event_id = records[0]["calendar_event_id"]

        attendees = []
        if student_email:
            attendees.append(student_email)
        if teacher_email:
            attendees.append(teacher_email)

        body = self._build_calendar_event(
            summary=summary, description=description,
            date=date, start_time=start_time, end_time=end_time,
            attendee_emails=attendees,
        )

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.put(
                    f"{CALENDAR_API_BASE}/calendars/primary/events/{event_id}",
                    params={"sendUpdates": "all"},
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    json=body, timeout=15.0,
                )

            if resp.status_code != 200:
                logger.error(f"Calendar update 失敗: {resp.status_code} {resp.text[:300]}")
                return False

            await supabase_service.pool.execute(
                "UPDATE booking_calendar_events SET last_synced_at = now(), updated_at = now() "
                "WHERE booking_id = $1 AND sync_status = 'synced'",
                booking_id,
            )

            logger.info(f"Booking {booking_id}: Calendar 事件更新成功 (event={event_id})")
            return True

        except Exception as e:
            logger.error(f"Calendar update 例外: {e}")
            return False

    async def cancel_calendar_event(self, booking_id: str) -> bool:
        """取消已同步的 Calendar 事件"""
        token = await self.get_active_token()
        if not token:
            return False

        records = await supabase_service.table_select(
            table="booking_calendar_events",
            select="calendar_event_id",
            filters={"booking_id": booking_id, "sync_status": "synced"},
        )
        if not records:
            return False

        event_id = records[0]["calendar_event_id"]

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    f"{CALENDAR_API_BASE}/calendars/primary/events/{event_id}",
                    params={"sendUpdates": "all"},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=15.0,
                )

            if resp.status_code not in (200, 204):
                logger.error(f"Calendar cancel 失敗: {resp.status_code} {resp.text[:300]}")
                return False

            await supabase_service.pool.execute(
                "UPDATE booking_calendar_events SET sync_status = 'cancelled', updated_at = now() "
                "WHERE booking_id = $1 AND sync_status = 'synced'",
                booking_id,
            )

            logger.info(f"Booking {booking_id}: Calendar 事件已取消 (event={event_id})")
            return True

        except Exception as e:
            logger.error(f"Calendar cancel 例外: {e}")
            return False

    # ============================================================
    # Internal
    # ============================================================

    async def _get_active_config(self) -> Optional[dict]:
        """從 DB 取得啟用中的 Google OAuth 設定"""
        rows = await supabase_service.table_select(
            table="google_drive_config",
            select="*",
            filters={"is_active": "eq.true"},
        )
        return rows[0] if rows else None


# 單例 + 向後相容別名
google_service = GoogleService()
google_drive_service = google_service
google_calendar_service = google_service
