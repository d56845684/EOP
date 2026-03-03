import secrets
from datetime import datetime, timedelta
from typing import Optional
from app.services.redis_service import redis_service

INVITE_TTL = 7 * 24 * 60 * 60  # 7 天


class InviteService:
    """邀請 Token 管理服務"""

    @staticmethod
    def _token_key(token: str) -> str:
        return f"invite:{token}"

    @staticmethod
    def _entity_key(entity_type: str, entity_id: str) -> str:
        return f"invite_entity:{entity_type}:{entity_id}"

    async def generate_token(
        self,
        entity_type: str,
        entity_id: str,
        email: str,
        name: str,
    ) -> tuple[str, datetime]:
        """產生邀請 token，回傳 (token, expires_at)"""
        # 失效該 entity 的舊 token
        entity_key = self._entity_key(entity_type, entity_id)
        old_token = await redis_service.get(entity_key)
        if old_token:
            await redis_service.delete(self._token_key(old_token))
            await redis_service.delete(entity_key)

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(seconds=INVITE_TTL)

        data = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "email": email,
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
        }

        await redis_service.set_json(self._token_key(token), data, expire_seconds=INVITE_TTL)
        await redis_service.set(entity_key, token, expire_seconds=INVITE_TTL)

        return token, expires_at

    async def validate_token(self, token: str) -> Optional[dict]:
        """驗證 token，回傳 token 資料（不消費）"""
        return await redis_service.get_json(self._token_key(token))

    async def consume_token(self, token: str) -> Optional[dict]:
        """消費 token（一次性），回傳 token 資料後刪除"""
        data = await redis_service.get_json(self._token_key(token))
        if not data:
            return None

        # 刪除 token 與反向索引
        await redis_service.delete(self._token_key(token))
        entity_key = self._entity_key(data["entity_type"], data["entity_id"])
        await redis_service.delete(entity_key)

        return data


invite_service = InviteService()
