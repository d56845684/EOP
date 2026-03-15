"""
權限服務 - 管理員工階層式權限
"""
import json
import uuid
from typing import Optional
from app.services.redis_service import redis_service
from app.services.supabase_service import supabase_service


class PermissionService:
    """員工權限管理服務"""

    # 權限等級對照表（與資料庫同步）
    PERMISSION_LEVELS = {
        'intern': 10,       # 工讀生
        'part_time': 20,    # 兼職員工
        'full_time': 30,    # 正式員工
        'admin': 100        # 管理員
    }

    # 等級名稱對照
    LEVEL_NAMES = {
        10: '工讀生',
        20: '兼職員工',
        30: '正式員工',
        100: '管理員'
    }

    # 快取過期時間（秒）
    CACHE_TTL = 300  # 5 分鐘

    def get_level_for_type(self, employee_type: Optional[str]) -> int:
        """取得員工類型對應的權限等級"""
        if not employee_type:
            return 0
        return self.PERMISSION_LEVELS.get(employee_type, 0)

    def get_type_for_level(self, level: int) -> Optional[str]:
        """取得權限等級對應的員工類型"""
        for emp_type, emp_level in self.PERMISSION_LEVELS.items():
            if emp_level == level:
                return emp_type
        return None

    def get_level_name(self, level: int) -> str:
        """取得權限等級名稱"""
        return self.LEVEL_NAMES.get(level, '未知')

    async def get_user_permission_level(self, user_id: str) -> int:
        """
        取得用戶的權限等級

        Args:
            user_id: 用戶 ID

        Returns:
            權限等級數值，非員工返回 0
        """
        # 嘗試從快取取得
        cache_key = f"permission_level:{user_id}"
        cached = await redis_service.get(cache_key)
        if cached is not None:
            return int(cached)

        # 從資料庫查詢
        try:
            result = await supabase_service.table_select(
                table="user_profiles",
                select="employee_subtype",
                filters={"id": f"eq.{user_id}"},
            )

            if result and len(result) > 0:
                employee_type = result[0].get("employee_subtype")
                level = self.get_level_for_type(employee_type)
            else:
                level = 0

            # 快取結果
            await redis_service.set(cache_key, str(level), ex=self.CACHE_TTL)
            return level

        except Exception:
            return 0

    async def get_user_employee_type(self, user_id: str) -> Optional[str]:
        """
        取得用戶的員工類型

        Args:
            user_id: 用戶 ID

        Returns:
            員工類型字串，非員工返回 None
        """
        # 嘗試從快取取得
        cache_key = f"employee_type:{user_id}"
        cached = await redis_service.get(cache_key)
        if cached is not None:
            return cached if cached != "null" else None

        # 從資料庫查詢
        try:
            result = await supabase_service.table_select(
                table="user_profiles",
                select="employee_subtype",
                filters={"id": f"eq.{user_id}"},
            )

            if result and len(result) > 0:
                employee_type = result[0].get("employee_subtype")
            else:
                employee_type = None

            # 快取結果
            cache_value = employee_type if employee_type else "null"
            await redis_service.set(cache_key, cache_value, ex=self.CACHE_TTL)
            return employee_type

        except Exception:
            return None

    async def check_permission(
        self,
        user_id: str,
        required_level: int
    ) -> bool:
        """
        檢查用戶是否有足夠的權限等級

        Args:
            user_id: 用戶 ID
            required_level: 所需的最低權限等級

        Returns:
            True 如果有足夠權限
        """
        user_level = await self.get_user_permission_level(user_id)
        return user_level >= required_level

    async def invalidate_user_cache(self, user_id: str) -> None:
        """
        清除用戶的權限快取

        Args:
            user_id: 用戶 ID
        """
        await redis_service.delete(f"permission_level:{user_id}")
        await redis_service.delete(f"employee_type:{user_id}")

    def is_higher_or_equal(
        self,
        user_type: Optional[str],
        required_type: str
    ) -> bool:
        """
        檢查用戶類型是否高於或等於所需類型

        Args:
            user_type: 用戶的員工類型
            required_type: 所需的員工類型

        Returns:
            True 如果權限足夠
        """
        user_level = self.get_level_for_type(user_type)
        required_level = self.get_level_for_type(required_type)
        return user_level >= required_level

    def can_manage(
        self,
        manager_type: Optional[str],
        target_type: Optional[str]
    ) -> bool:
        """
        檢查管理者是否可以管理目標用戶

        規則：只能管理權限等級低於自己的用戶

        Args:
            manager_type: 管理者的員工類型
            target_type: 目標的員工類型

        Returns:
            True 如果可以管理
        """
        manager_level = self.get_level_for_type(manager_type)
        target_level = self.get_level_for_type(target_type)

        # 管理員可以管理任何人
        if manager_level >= 100:
            return True

        # 其他員工只能管理等級比自己低的
        return manager_level > target_level

    # ================================================================
    # Page Permission 快取
    # ================================================================

    PAGE_PERM_CACHE_TTL = 300  # 5 分鐘

    async def get_effective_page_keys(self, role_id: str, user_id: str) -> set[str]:
        """
        取得用戶有效的 page keys（含 role_pages + user overrides）。
        effective = (role_pages ∪ user_grants) \\ user_revokes

        結果以 Redis 快取，TTL 300 秒。

        Args:
            role_id: 角色 UUID
            user_id: 用戶 UUID
        """
        cache_key = f"page_perm:{user_id}"
        cached = await redis_service.get(cache_key)
        if cached is not None:
            return set(json.loads(cached))

        try:
            uid = uuid.UUID(user_id)
            rid = uuid.UUID(role_id) if role_id else None

            keys: set[str] = set()

            # role_pages → page keys (use role_id UUID)
            if rid:
                role_rows = await supabase_service.pool.fetch(
                    """
                    SELECT p.key
                    FROM role_pages rp
                    JOIN pages p ON p.id = rp.page_id
                    WHERE rp.role_id = $1 AND p.is_active = TRUE
                    """,
                    rid,
                )
                keys = {r["key"] for r in role_rows}

            # user overrides
            override_rows = await supabase_service.pool.fetch(
                """
                SELECT p.key, upo.access_type
                FROM user_page_overrides upo
                JOIN pages p ON p.id = upo.page_id
                WHERE upo.user_id = $1 AND p.is_active = TRUE
                """,
                uid,
            )
            for row in override_rows:
                if row["access_type"] == "grant":
                    keys.add(row["key"])
                else:  # revoke
                    keys.discard(row["key"])

            # 快取
            await redis_service.set(cache_key, json.dumps(sorted(keys)), expire_seconds=self.PAGE_PERM_CACHE_TTL)
            return keys

        except Exception as exc:
            import logging
            logging.getLogger(__name__).exception("get_effective_page_keys failed for role_id=%s user_id=%s", role_id, user_id)
            return set()

    async def invalidate_page_perm_cache(self, user_id: str) -> None:
        """清除單一用戶的 page permission 快取"""
        await redis_service.delete(f"page_perm:{user_id}")

    async def invalidate_role_page_perm_cache(self, role_id: str) -> None:
        """清除該角色所有用戶的 page permission 快取"""
        try:
            rid = uuid.UUID(role_id)
            rows = await supabase_service.pool.fetch(
                "SELECT id FROM user_profiles WHERE role_id = $1",
                rid,
            )
            for row in rows:
                await redis_service.delete(f"page_perm:{row['id']}")
        except Exception:
            pass


# 單例
permission_service = PermissionService()
