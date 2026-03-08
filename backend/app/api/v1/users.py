import uuid
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from app.core.dependencies import (
    get_current_user, require_staff, require_page_permission, CurrentUser
)
from app.services.supabase_service import supabase_service
from app.schemas.response import DataResponse, PaginatedResponse, BaseResponse
from app.schemas.user import UserProfile, AccountInfo, AccountUpdate

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["用戶管理"])


@router.get("/profile", response_model=DataResponse[UserProfile])
async def get_profile(
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得當前用戶完整資料"""
    # 根據 entity ID 查詢對應的表
    if current_user.student_id:
        table = "students"
    elif current_user.teacher_id:
        table = "teachers"
    else:
        table = "employees"

    # 查詢 user_profile
    profiles = await supabase_service.table_select(
        table="user_profiles",
        select="*",
        filters={"id": current_user.user_id},
    )

    entity_data = {}
    if profiles and len(profiles) > 0:
        profile = profiles[0]
        entity_id = profile.get(f"{table.rstrip('s')}_id")

        if entity_id:
            entities = await supabase_service.table_select(
                table=table,
                select="*",
                filters={"id": entity_id},
            )
            if entities:
                entity_data = entities[0]

    return DataResponse(
        data=UserProfile(
            id=current_user.user_id,
            email=current_user.email,
            role=current_user.role,
            name=entity_data.get("name"),
            avatar_url=entity_data.get("avatar_url"),
            is_active=entity_data.get("is_active", True)
        )
    )


@router.get("/", response_model=PaginatedResponse[AccountInfo])
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    role: Optional[str] = Query(None, description="角色篩選"),
    search: Optional[str] = Query(None, description="搜尋 email/name"),
    current_user: CurrentUser = Depends(require_page_permission("employees.list")),
):
    """列出所有帳號（含 email、名稱）"""
    try:
        # Build SQL with JOINs to get email and name
        params = []
        where_clauses = []

        base_sql = """
            SELECT
                up.id,
                u.email,
                r.key AS role,
                up.role_id,
                up.employee_subtype,
                up.is_active,
                COALESCE(up.is_protected, FALSE) AS is_protected,
                up.created_at,
                COALESCE(e.name, t.name, s.name) AS name
            FROM user_profiles up
            JOIN public.users u ON u.id = up.id
            LEFT JOIN roles r ON r.id = up.role_id
            LEFT JOIN employees e ON e.id = up.employee_id
            LEFT JOIN teachers t ON t.id = up.teacher_id
            LEFT JOIN students s ON s.id = up.student_id
        """

        if role:
            params.append(role)
            where_clauses.append(f"r.key = ${len(params)}")

        if search:
            params.append(f"%{search}%")
            idx = len(params)
            where_clauses.append(
                f"(u.email ILIKE ${idx} OR COALESCE(e.name, t.name, s.name) ILIKE ${idx})"
            )

        where_sql = ""
        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)

        # Count total
        count_sql = f"SELECT COUNT(*) FROM user_profiles up JOIN public.users u ON u.id = up.id LEFT JOIN roles r ON r.id = up.role_id LEFT JOIN employees e ON e.id = up.employee_id LEFT JOIN teachers t ON t.id = up.teacher_id LEFT JOIN students s ON s.id = up.student_id{where_sql}"
        total_row = await supabase_service.pool.fetchrow(count_sql, *params)
        total = total_row[0] if total_row else 0

        # Query with pagination
        offset = (page - 1) * per_page
        params.append(per_page)
        limit_idx = len(params)
        params.append(offset)
        offset_idx = len(params)

        data_sql = f"{base_sql}{where_sql} ORDER BY up.created_at DESC LIMIT ${limit_idx} OFFSET ${offset_idx}"
        rows = await supabase_service.pool.fetch(data_sql, *params)

        users = []
        for row in rows:
            d = supabase_service._row_to_dict(row)
            users.append(AccountInfo(
                id=d["id"],
                email=d["email"],
                name=d.get("name"),
                role=d["role"],
                role_id=str(d["role_id"]) if d.get("role_id") else None,
                employee_subtype=d.get("employee_subtype"),
                is_active=d.get("is_active", True),
                is_protected=d.get("is_protected", False),
                created_at=d.get("created_at"),
            ))

        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        return PaginatedResponse(
            data=users,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("列出帳號失敗")
        raise HTTPException(status_code=500, detail=f"列出帳號失敗: {e}")


@router.put("/{user_id}", response_model=DataResponse[AccountInfo])
async def update_user(
    user_id: str,
    data: AccountUpdate,
    current_user: CurrentUser = Depends(require_page_permission("employees.edit")),
):
    """更新帳號角色/狀態"""
    try:
        uid = uuid.UUID(user_id)

        # Check exists & is_protected
        profile = await supabase_service.pool.fetchrow(
            "SELECT id, role_id, employee_subtype, is_active, COALESCE(is_protected, FALSE) AS is_protected FROM user_profiles WHERE id = $1",
            uid,
        )
        if not profile:
            raise HTTPException(status_code=404, detail="帳號不存在")
        if profile["is_protected"]:
            raise HTTPException(status_code=403, detail="此帳號受保護，無法修改")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        # If employee_subtype changes, also update employees table
        # (DB trigger sync_employee_subtype reads from employees.employee_type)
        if "employee_subtype" in update_data:
            employee_id = await supabase_service.pool.fetchval(
                "SELECT employee_id FROM user_profiles WHERE id = $1", uid
            )
            if employee_id:
                await supabase_service.pool.execute(
                    "UPDATE employees SET employee_type = $1 WHERE id = $2",
                    update_data["employee_subtype"], employee_id,
                )

        # Convert role_id string to UUID for DB update
        if "role_id" in update_data:
            update_data["role_id"] = uuid.UUID(update_data["role_id"])

        # Update user_profiles
        sets = []
        params = [uid]
        for k, v in update_data.items():
            params.append(v)
            sets.append(f"{k} = ${len(params)}")

        await supabase_service.pool.execute(
            f"UPDATE user_profiles SET {', '.join(sets)} WHERE id = $1",
            *params,
        )

        # Re-fetch full account info
        row = await supabase_service.pool.fetchrow(
            """
            SELECT up.id, u.email, r.key AS role, up.role_id,
                   up.employee_subtype, up.is_active,
                   COALESCE(up.is_protected, FALSE) AS is_protected, up.created_at,
                   COALESCE(e.name, t.name, s.name) AS name
            FROM user_profiles up
            JOIN public.users u ON u.id = up.id
            LEFT JOIN roles r ON r.id = up.role_id
            LEFT JOIN employees e ON e.id = up.employee_id
            LEFT JOIN teachers t ON t.id = up.teacher_id
            LEFT JOIN students s ON s.id = up.student_id
            WHERE up.id = $1
            """,
            uid,
        )
        d = supabase_service._row_to_dict(row)
        account = AccountInfo(
            id=d["id"], email=d["email"], name=d.get("name"),
            role=d["role"], role_id=str(d["role_id"]) if d.get("role_id") else None,
            employee_subtype=d.get("employee_subtype"),
            is_active=d.get("is_active", True),
            is_protected=d.get("is_protected", False),
            created_at=d.get("created_at"),
        )

        return DataResponse(message="帳號更新成功", data=account)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("更新帳號失敗")
        raise HTTPException(status_code=500, detail=f"更新帳號失敗: {e}")


@router.delete("/{user_id}", response_model=BaseResponse)
async def deactivate_user(
    user_id: str,
    current_user: CurrentUser = Depends(require_page_permission("employees.delete")),
):
    """停用帳號（設 is_active=false）"""
    try:
        uid = uuid.UUID(user_id)

        profile = await supabase_service.pool.fetchrow(
            "SELECT id, COALESCE(is_protected, FALSE) AS is_protected FROM user_profiles WHERE id = $1",
            uid,
        )
        if not profile:
            raise HTTPException(status_code=404, detail="帳號不存在")
        if profile["is_protected"]:
            raise HTTPException(status_code=403, detail="此帳號受保護，無法停用")

        await supabase_service.table_update(
            table="user_profiles",
            data={"is_active": False},
            filters={"id": user_id},
        )

        return BaseResponse(message="帳號已停用")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("停用帳號失敗")
        raise HTTPException(status_code=500, detail=f"停用帳號失敗: {e}")
