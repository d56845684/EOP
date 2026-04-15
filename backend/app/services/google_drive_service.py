"""
Google Drive OAuth Service

管理員做一次 OAuth 授權，系統存 refresh token，
Lambda 透過 internal API 取得 access token 上傳錄影到管理員的個人 Drive。
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
GOOGLE_DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file openid email profile"


class GoogleDriveService:

    def get_oauth_authorize_url(self, state: str = "") -> str:
        """產生 Google OAuth 授權 URL"""
        params = {
            "client_id": settings.GOOGLE_DRIVE_OAUTH_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_DRIVE_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": GOOGLE_DRIVE_SCOPE,
            "access_type": "offline",     # 取得 refresh_token
            "prompt": "consent",          # 強制顯示同意畫面（確保拿到 refresh_token）
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

            # 更新 DB
            await supabase_service.table_update(
                table="google_drive_config",
                data={
                    "google_access_token": new_access,
                    "google_token_expires_at": expires_at.isoformat(),
                    "updated_at": "now()",
                },
                filters={"id": config["id"]},
            )

            logger.info(f"Google Drive token refreshed, expires_at={expires_at.isoformat()}")
            return new_access

        except Exception as e:
            logger.error(f"Google token refresh 例外: {e}")
            return None

    async def get_active_token(self) -> Optional[str]:
        """取得可用的 access_token，過期自動 refresh"""
        config = await self._get_active_config()
        if not config:
            return None

        # 檢查過期（5 分鐘緩衝）
        expires_at = config.get("google_token_expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5):
                return await self.refresh_access_token()

        return config.get("google_access_token")

    async def get_drive_config(self) -> Optional[dict]:
        """取得完整 Drive 設定（mode, folder_id, email 等）"""
        return await self._get_active_config()

    async def _get_active_config(self) -> Optional[dict]:
        """從 DB 取得啟用中的 Google Drive 設定"""
        rows = await supabase_service.table_select(
            table="google_drive_config",
            select="*",
            filters={"is_active": "eq.true"},
        )
        return rows[0] if rows else None


google_drive_service = GoogleDriveService()
