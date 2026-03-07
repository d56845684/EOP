import math
import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, require_staff, require_page_permission, CurrentUser
from app.services.permission_service import permission_service
from app.schemas.response import BaseResponse, DataResponse
from app.schemas.page_permission import (
    PageCreate, PageUpdate, PageResponse, PageListResponse,
    RolePagesResponse, RolePagesBatchSet,
    UserPageOverrideItem, UserPageOverridesResponse, UserPageOverridesBatchSet,
    MyPermissionsResponse,
    RoleInfo, RoleListResponse, RoleCreate, RoleUpdate,
)

import logging
logger = logging.getLogger(__name__)

# ========== Routers ==========

router = APIRouter(tags=["頁面權限管理"])

PAGE_SELECT = "id,key,name,description,parent_key,sort_order,is_active,created_at,updated_at"


# ============================================================
# Pages CRUD（require_staff）
# ============================================================

@router.get("/pages", response_model=PageListResponse)
async def list_pages(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    is_active: Optional[bool] = Query(None),
    current_user: CurrentUser = Depends(require_page_permission("permissions.pages")),
):
    """取得頁面列表"""
    try:
        filters = {}
        if is_active is not None:
            filters["is_active"] = f"eq.{str(is_active).lower()}"

        all_items = await supabase_service.table_select(
            table="pages", select="id", filters=filters if filters else None
        )
        total = len(all_items)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        pages_data = await supabase_service.table_select_with_pagination(
            table="pages", select=PAGE_SELECT,
            filters=filters if filters else None,
            order_by="sort_order.asc,key.asc",
            limit=per_page, offset=offset,
        )

        return PageListResponse(
            data=[PageResponse(**p) for p in pages_data],
            total=total, page=page, per_page=per_page, total_pages=total_pages,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得頁面列表失敗: {e}")


@router.post("/pages", response_model=DataResponse[PageResponse])
async def create_page(
    data: PageCreate,
    current_user: CurrentUser = Depends(require_page_permission("permissions.pages")),
):
    """建立頁面"""
    try:
        existing = await supabase_service.table_select(
            table="pages", select="id", filters={"key": data.key}
        )
        if existing:
            raise HTTPException(status_code=400, detail=f"頁面 key '{data.key}' 已存在")

        result = await supabase_service.table_insert(
            table="pages", data=data.model_dump()
        )
        return DataResponse(message="頁面建立成功", data=PageResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立頁面失敗: {e}")


@router.put("/pages/{page_id}", response_model=DataResponse[PageResponse])
async def update_page(
    page_id: str,
    data: PageUpdate,
    current_user: CurrentUser = Depends(require_page_permission("permissions.pages")),
):
    """更新頁面"""
    try:
        existing = await supabase_service.table_select(
            table="pages", select="id,key", filters={"id": page_id}
        )
        if not existing:
            raise HTTPException(status_code=404, detail="頁面不存在")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        # check key uniqueness if changing
        if "key" in update_data and update_data["key"] != existing[0]["key"]:
            dup = await supabase_service.table_select(
                table="pages", select="id", filters={"key": update_data["key"]}
            )
            if dup:
                raise HTTPException(status_code=400, detail=f"頁面 key '{update_data['key']}' 已存在")

        result = await supabase_service.table_update(
            table="pages", data=update_data, filters={"id": page_id}
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新失敗")

        return DataResponse(message="頁面更新成功", data=PageResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新頁面失敗: {e}")


@router.delete("/pages/{page_id}", response_model=BaseResponse)
async def delete_page(
    page_id: str,
    current_user: CurrentUser = Depends(require_page_permission("permissions.pages")),
):
    """停用頁面（軟刪除 is_active=False）"""
    try:
        existing = await supabase_service.table_select(
            table="pages", select="id", filters={"id": page_id}
        )
        if not existing:
            raise HTTPException(status_code=404, detail="頁面不存在")

        result = await supabase_service.table_update(
            table="pages",
            data={"is_active": False},
            filters={"id": page_id},
        )
        if not result:
            raise HTTPException(status_code=500, detail="停用失敗")

        return BaseResponse(message="頁面已停用")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停用頁面失敗: {e}")


# ============================================================
# Roles CRUD（require_staff）
# ============================================================

@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    current_user: CurrentUser = Depends(require_page_permission("permissions.roles")),
):
    """取得所有角色及其頁面數量"""
    try:
        rows = await supabase_service.pool.fetch(
            """
            SELECT r.id, r.key, r.name, r.description, r.is_system,
                   COUNT(rp.page_id) FILTER (WHERE p.is_active = TRUE) AS page_count
            FROM roles r
            LEFT JOIN role_pages rp ON rp.role_id = r.id
            LEFT JOIN pages p ON p.id = rp.page_id
            GROUP BY r.id, r.key, r.name, r.description, r.is_system
            ORDER BY r.is_system DESC, r.created_at
            """
        )
        data = [
            RoleInfo(
                id=str(r["id"]), key=r["key"], name=r["name"],
                description=r["description"],
                is_system=r["is_system"],
                page_count=r["page_count"],
            )
            for r in rows
        ]
        return RoleListResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得角色列表失敗: {e}")


@router.post("/roles", response_model=DataResponse[RoleInfo])
async def create_role(
    data: RoleCreate,
    current_user: CurrentUser = Depends(require_page_permission("permissions.roles")),
):
    """建立新角色"""
    try:
        existing = await supabase_service.pool.fetchrow(
            "SELECT id FROM roles WHERE key = $1", data.key
        )
        if existing:
            raise HTTPException(status_code=400, detail=f"角色 '{data.key}' 已存在")

        new_id = uuid.uuid4()
        await supabase_service.pool.execute(
            "INSERT INTO roles (id, key, name, description) VALUES ($1, $2, $3, $4)",
            new_id, data.key, data.name, data.description or "",
        )

        return DataResponse(
            message="角色建立成功",
            data=RoleInfo(id=str(new_id), key=data.key, name=data.name, description=data.description, is_system=False, page_count=0),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立角色失敗: {e}")


@router.put("/roles/{role_id}", response_model=DataResponse[RoleInfo])
async def update_role(
    role_id: str,
    data: RoleUpdate,
    current_user: CurrentUser = Depends(require_page_permission("permissions.roles")),
):
    """更新角色名稱/描述"""
    try:
        rid = uuid.UUID(role_id)
        existing = await supabase_service.pool.fetchrow(
            "SELECT id, key, name, description, is_system FROM roles WHERE id = $1", rid
        )
        if not existing:
            raise HTTPException(status_code=404, detail="角色不存在")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        # Build SET clause
        sets = []
        params = [rid]
        for k, v in update_data.items():
            params.append(v)
            sets.append(f"{k} = ${len(params)}")

        row = await supabase_service.pool.fetchrow(
            f"UPDATE roles SET {', '.join(sets)} WHERE id = $1 RETURNING id, key, name, description, is_system",
            *params,
        )
        if not row:
            raise HTTPException(status_code=500, detail="更新失敗")

        # Get page count
        count_row = await supabase_service.pool.fetchrow(
            """SELECT COUNT(*) AS cnt FROM role_pages rp
               JOIN pages p ON p.id = rp.page_id AND p.is_active = TRUE
               WHERE rp.role_id = $1""",
            rid,
        )

        return DataResponse(
            message="角色更新成功",
            data=RoleInfo(
                id=str(row["id"]), key=row["key"], name=row["name"],
                description=row["description"],
                is_system=row["is_system"],
                page_count=count_row["cnt"] if count_row else 0,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新角色失敗: {e}")


@router.delete("/roles/{role_id}", response_model=BaseResponse)
async def delete_role(
    role_id: str,
    current_user: CurrentUser = Depends(require_page_permission("permissions.roles")),
):
    """刪除角色（系統內建角色不可刪除）"""
    try:
        rid = uuid.UUID(role_id)
        existing = await supabase_service.pool.fetchrow(
            "SELECT id, key, is_system FROM roles WHERE id = $1", rid
        )
        if not existing:
            raise HTTPException(status_code=404, detail="角色不存在")
        if existing["is_system"]:
            raise HTTPException(status_code=403, detail="系統內建角色無法刪除")

        # Check if any user is using this role
        users_count = await supabase_service.pool.fetchval(
            "SELECT COUNT(*) FROM user_profiles WHERE role_id = $1", rid
        )
        if users_count and users_count > 0:
            raise HTTPException(status_code=400, detail=f"仍有 {users_count} 個帳號使用此角色，無法刪除")

        # Delete role_pages first, then role
        async with supabase_service.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM role_pages WHERE role_id = $1", rid)
                await conn.execute("DELETE FROM roles WHERE id = $1", rid)

        return BaseResponse(message="角色已刪除")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除角色失敗: {e}")


# ============================================================
# Role-Pages（require_staff）
# ============================================================

@router.get("/role-pages", response_model=RolePagesResponse)
async def get_role_pages(
    role_id: str = Query(..., description="角色 UUID"),
    current_user: CurrentUser = Depends(require_page_permission("permissions.roles")),
):
    """查看角色預設頁面"""
    try:
        rid = uuid.UUID(role_id)
        rows = await supabase_service.pool.fetch(
            """
            SELECT p.id, p.key, p.name, p.description, p.parent_key,
                   p.sort_order, p.is_active, p.created_at, p.updated_at
            FROM role_pages rp
            JOIN pages p ON p.id = rp.page_id
            WHERE rp.role_id = $1 AND p.is_active = TRUE
            ORDER BY p.sort_order, p.key
            """,
            rid,
        )
        pages = [PageResponse(**supabase_service._row_to_dict(r)) for r in rows]
        return RolePagesResponse(role_id=role_id, pages=pages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得角色頁面失敗: {e}")


@router.put("/role-pages", response_model=RolePagesResponse)
async def set_role_pages(
    data: RolePagesBatchSet,
    current_user: CurrentUser = Depends(require_page_permission("permissions.roles")),
):
    """批次設定角色頁面（取代現有設定）"""
    try:
        rid = uuid.UUID(data.role_id)
        async with supabase_service.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM role_pages WHERE role_id = $1", rid
                )
                if data.page_ids:
                    await conn.executemany(
                        "INSERT INTO role_pages (id, role_id, page_id) VALUES ($1, $2, $3)",
                        [
                            (uuid.uuid4(), rid, uuid.UUID(pid))
                            for pid in data.page_ids
                        ],
                    )

        # 清除該角色所有用戶的 page permission 快取
        await permission_service.invalidate_role_page_perm_cache(data.role_id)

        # Return updated result
        return await get_role_pages(role_id=data.role_id, current_user=current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"設定角色頁面失敗: {e}")


# ============================================================
# User Page Overrides（require_staff）
# ============================================================

@router.get("/user-pages/{user_id}", response_model=UserPageOverridesResponse)
async def get_user_page_overrides(
    user_id: str,
    current_user: CurrentUser = Depends(require_page_permission("permissions.users")),
):
    """查看用戶頁面覆寫"""
    try:
        rows = await supabase_service.pool.fetch(
            """
            SELECT upo.id, upo.page_id, p.key AS page_key, p.name AS page_name,
                   upo.access_type, upo.created_at
            FROM user_page_overrides upo
            JOIN pages p ON p.id = upo.page_id
            WHERE upo.user_id = $1
            ORDER BY p.sort_order, p.key
            """,
            uuid.UUID(user_id),
        )
        overrides = [
            UserPageOverrideItem(**supabase_service._row_to_dict(r)) for r in rows
        ]
        return UserPageOverridesResponse(user_id=user_id, overrides=overrides)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得用戶覆寫失敗: {e}")


@router.put("/user-pages/{user_id}", response_model=UserPageOverridesResponse)
async def set_user_page_overrides(
    user_id: str,
    data: UserPageOverridesBatchSet,
    current_user: CurrentUser = Depends(require_page_permission("permissions.users")),
):
    """批次設定用戶頁面覆寫（取代現有設定）"""
    try:
        uid = uuid.UUID(user_id)
        async with supabase_service.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM user_page_overrides WHERE user_id = $1", uid
                )
                if data.overrides:
                    await conn.executemany(
                        """INSERT INTO user_page_overrides (id, user_id, page_id, access_type)
                           VALUES ($1, $2, $3, $4)""",
                        [
                            (uuid.uuid4(), uid, uuid.UUID(o.page_id), o.access_type.value)
                            for o in data.overrides
                        ],
                    )

        # 清除該用戶的 page permission 快取
        await permission_service.invalidate_page_perm_cache(user_id)

        return await get_user_page_overrides(user_id=user_id, current_user=current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"設定用戶覆寫失敗: {e}")


# ============================================================
# Current User Permissions
# ============================================================

@router.get("/permissions/me", response_model=MyPermissionsResponse)
async def get_my_permissions(
    current_user: CurrentUser = Depends(get_current_user),
):
    """取得當前用戶有效頁面權限

    effective = (role_defaults ∪ personal_grants) \\ personal_revokes
    """
    try:
        role = current_user.role
        role_id = current_user.role_id
        user_id = uuid.UUID(current_user.user_id) if current_user.user_id != "service-account" else None

        # 1. role defaults (use role_id UUID)
        role_pages_map = {}
        if role_id:
            rid = uuid.UUID(role_id)
            role_rows = await supabase_service.pool.fetch(
                """
                SELECT p.id, p.key, p.name, p.description, p.parent_key,
                       p.sort_order, p.is_active, p.created_at, p.updated_at
                FROM role_pages rp
                JOIN pages p ON p.id = rp.page_id
                WHERE rp.role_id = $1 AND p.is_active = TRUE
                """,
                rid,
            )
            role_pages_map = {
                str(r["id"]): supabase_service._row_to_dict(r) for r in role_rows
            }

        grants = {}
        revokes = set()

        # 2. personal overrides
        if user_id:
            override_rows = await supabase_service.pool.fetch(
                """
                SELECT upo.page_id, upo.access_type,
                       p.id, p.key, p.name, p.description, p.parent_key,
                       p.sort_order, p.is_active, p.created_at, p.updated_at
                FROM user_page_overrides upo
                JOIN pages p ON p.id = upo.page_id
                WHERE upo.user_id = $1 AND p.is_active = TRUE
                """,
                user_id,
            )
            for row in override_rows:
                d = supabase_service._row_to_dict(row)
                pid = d["page_id"]
                if d["access_type"] == "grant":
                    grants[pid] = d
                else:
                    revokes.add(pid)

        # 3. effective = (role_defaults ∪ grants) \ revokes
        effective = {}
        for pid, page_data in role_pages_map.items():
            if pid not in revokes:
                effective[pid] = page_data
        for pid, page_data in grants.items():
            if pid not in revokes:
                effective[pid] = page_data

        # Sort by sort_order
        sorted_pages = sorted(effective.values(), key=lambda p: (p.get("sort_order", 0), p.get("key", "")))
        page_keys = [p["key"] for p in sorted_pages]
        pages = [PageResponse(**p) for p in sorted_pages]

        return MyPermissionsResponse(
            role=role,
            page_keys=page_keys,
            pages=pages,
        )
    except Exception as e:
        logger.exception("取得權限失敗")
        raise HTTPException(status_code=500, detail=f"取得權限失敗: {e}")
