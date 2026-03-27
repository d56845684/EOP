from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_page_permission, get_user_employee_id
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime
import math
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/employees", tags=["員工管理"])

EMPLOYEE_SELECT = "id,employee_no,employee_type,name,email,phone,address,hire_date,termination_date,is_active,email_verified_at,created_at,updated_at"


async def enrich_employee(emp: dict) -> dict:
    """從 user_profiles 補上 has_account / role_id / role_name"""
    import uuid as _uuid
    eid = emp.get("id")
    if not eid:
        emp["has_account"] = False
        emp["role_id"] = None
        emp["role_name"] = None
        return emp
    row = await supabase_service.pool.fetchrow(
        """SELECT up.id, r.id AS role_id, r.name AS role_name
           FROM user_profiles up
           JOIN roles r ON r.id = up.role_id
           WHERE up.employee_id = $1""",
        _uuid.UUID(eid) if isinstance(eid, str) else eid,
    )
    if row:
        emp["has_account"] = True
        emp["role_id"] = str(row["role_id"])
        emp["role_name"] = row["role_name"]
    else:
        emp["has_account"] = False
        emp["role_id"] = None
        emp["role_name"] = None
    return emp


@router.get("/roles", tags=["員工管理"])
async def list_roles_for_employees(
    current_user: CurrentUser = Depends(require_page_permission("employees.list"))
):
    """取得可指定的角色列表"""
    try:
        rows = await supabase_service.pool.fetch(
            "SELECT id, key, name FROM roles ORDER BY key"
        )
        return {"data": [{"id": str(r["id"]), "key": r["key"], "name": r["name"]} for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得角色列表失敗: {str(e)}")


@router.get("", response_model=EmployeeListResponse)
async def list_employees(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜尋（編號/姓名/email）"),
    is_active: Optional[bool] = Query(None),
    employee_type: Optional[str] = Query(None, description="員工類型 (admin/full_time/part_time/intern)"),
    current_user: CurrentUser = Depends(require_page_permission("employees.list"))
):
    """取得員工列表（僅限員工）"""
    if not current_user.is_staff():
        raise HTTPException(status_code=403, detail="僅限員工存取")
    try:
        filters = {"is_deleted": "eq.false"}
        if is_active is not None:
            filters["is_active"] = f"eq.{str(is_active).lower()}"
        if employee_type:
            filters["employee_type"] = f"eq.{employee_type}"

        total = await supabase_service.table_count(table="employees", filters=filters)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        employees = await supabase_service.table_select_with_pagination(
            table="employees", select=EMPLOYEE_SELECT, filters=filters,
            order_by="created_at.desc", limit=per_page, offset=offset
        )

        if search:
            s = search.lower()
            employees = [
                emp for emp in employees
                if s in emp.get("employee_no", "").lower()
                or s in emp.get("name", "").lower()
                or s in emp.get("email", "").lower()
            ]

        for emp in employees:
            await enrich_employee(emp)

        return EmployeeListResponse(
            data=[EmployeeResponse(**emp) for emp in employees],
            total=total, page=page, per_page=per_page, total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得員工列表失敗: {str(e)}")


@router.get("/{employee_id}", response_model=DataResponse[EmployeeResponse])
async def get_employee(
    employee_id: str,
    current_user: CurrentUser = Depends(require_page_permission("employees.list"))
):
    """取得單一員工（僅限員工）"""
    if not current_user.is_staff():
        raise HTTPException(status_code=403, detail="僅限員工存取")
    try:
        result = await supabase_service.table_select(
            table="employees", select=EMPLOYEE_SELECT,
            filters={"id": employee_id, "is_deleted": "eq.false"}
        )
        if not result:
            raise HTTPException(status_code=404, detail="員工不存在")
        enriched = await enrich_employee(result[0])
        return DataResponse(data=EmployeeResponse(**enriched))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得員工失敗: {str(e)}")


@router.post("", response_model=DataResponse[EmployeeResponse])
async def create_employee(
    data: EmployeeCreate,
    current_user: CurrentUser = Depends(require_page_permission("employees.create"))
):
    """建立員工（僅限管理員）"""
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="僅限管理員操作")
    try:
        existing = await supabase_service.table_select(
            table="employees", select="id",
            filters={"employee_no": data.employee_no, "is_deleted": "eq.false"}
        )
        if existing:
            raise HTTPException(status_code=400, detail="員工編號已存在")

        existing_email = await supabase_service.table_select(
            table="employees", select="id",
            filters={"email": data.email, "is_deleted": "eq.false"}
        )
        if existing_email:
            raise HTTPException(status_code=400, detail="Email 已存在")

        employee_data = data.model_dump()
        if employee_data.get("hire_date"):
            employee_data["hire_date"] = employee_data["hire_date"].isoformat()
        if employee_data.get("termination_date"):
            employee_data["termination_date"] = employee_data["termination_date"].isoformat()

        creator_employee_id = await get_user_employee_id(current_user.user_id)
        if creator_employee_id:
            employee_data["created_by"] = creator_employee_id

        result = await supabase_service.table_insert(
            table="employees", data=employee_data
        )
        if not result:
            raise HTTPException(status_code=500, detail="建立員工失敗")

        enriched = await enrich_employee(result)
        return DataResponse(message="員工建立成功", data=EmployeeResponse(**enriched))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立員工失敗: {str(e)}")


@router.put("/{employee_id}", response_model=DataResponse[EmployeeResponse])
async def update_employee(
    employee_id: str,
    data: EmployeeUpdate,
    current_user: CurrentUser = Depends(require_page_permission("employees.edit"))
):
    """更新員工（僅限管理員）"""
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="僅限管理員操作")
    try:
        existing = await supabase_service.table_select(
            table="employees", select="id,employee_no,email,employee_type",
            filters={"id": employee_id, "is_deleted": "eq.false"}
        )
        if not existing:
            raise HTTPException(status_code=404, detail="員工不存在")

        if data.email and data.email != existing[0]["email"]:
            dup = await supabase_service.table_select(
                table="employees", select="id",
                filters={"email": data.email, "is_deleted": "eq.false"}
            )
            if dup:
                raise HTTPException(status_code=400, detail="Email 已存在")

        # role_id 不寫 employees 表，單獨處理
        requested_role_id = data.role_id
        employee_update = {k: v for k, v in data.model_dump().items() if v is not None}
        employee_update.pop("role_id", None)  # 不寫入 employees 表

        if "hire_date" in employee_update and employee_update["hire_date"]:
            employee_update["hire_date"] = employee_update["hire_date"].isoformat()
        if "termination_date" in employee_update and employee_update["termination_date"]:
            employee_update["termination_date"] = employee_update["termination_date"].isoformat()

        if not employee_update and not requested_role_id:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = existing[0]
        if employee_update:
            result = await supabase_service.table_update(
                table="employees", data=employee_update, filters={"id": employee_id}
            )
            if not result:
                raise HTTPException(status_code=500, detail="更新員工失敗")

        # 同步 user_profiles 角色（僅限已有帳號的員工）
        try:
            profile = await supabase_service.table_select(
                table="user_profiles", select="id,role_id",
                filters={"employee_id": employee_id},
            )
            if profile:
                sync_data: dict = {}
                # 直接指定 role_id → 寫入 user_profiles
                if requested_role_id:
                    sync_data["role_id"] = requested_role_id
                elif data.employee_type and data.employee_type != existing[0].get("employee_type"):
                    role_key = "admin" if data.employee_type == "admin" else "employee"
                    role_row = await supabase_service.pool.fetchrow(
                        "SELECT id FROM roles WHERE key = $1", role_key
                    )
                    if role_row:
                        sync_data["role_id"] = str(role_row["id"])
                if data.employee_type:
                    sync_data["employee_subtype"] = data.employee_type
            elif requested_role_id:
                raise HTTPException(status_code=400, detail="此員工尚未建立帳號，無法設定角色")
                if sync_data:
                    await supabase_service.table_update(
                        table="user_profiles",
                        data=sync_data,
                        filters={"id": profile[0]["id"]},
                    )
                    logger.info(f"Employee {employee_id}: user_profiles 同步 {sync_data}")
        except Exception as sync_err:
            logger.warning(f"Employee {employee_id}: 同步角色失敗: {sync_err}")

        enriched = await enrich_employee(result)
        return DataResponse(message="員工更新成功", data=EmployeeResponse(**enriched))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新員工失敗: {str(e)}")


@router.delete("/{employee_id}", response_model=BaseResponse)
async def delete_employee(
    employee_id: str,
    current_user: CurrentUser = Depends(require_page_permission("employees.delete"))
):
    """刪除員工（軟刪除，僅限管理員）"""
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="僅限管理員操作")
    try:
        existing = await supabase_service.table_select(
            table="employees", select="id",
            filters={"id": employee_id, "is_deleted": "eq.false"}
        )
        if not existing:
            raise HTTPException(status_code=404, detail="員工不存在")

        delete_data = {
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
        }
        creator_employee_id = await get_user_employee_id(current_user.user_id)
        if creator_employee_id:
            delete_data["deleted_by"] = creator_employee_id

        result = await supabase_service.table_update(
            table="employees", data=delete_data, filters={"id": employee_id}
        )
        if not result:
            raise HTTPException(status_code=500, detail="刪除員工失敗")

        return BaseResponse(message="員工刪除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除員工失敗: {str(e)}")
