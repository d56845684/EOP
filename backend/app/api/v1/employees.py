from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_page_permission, get_user_employee_id
from app.core.error_codes import ErrorCode
from app.core.exceptions import bad_request, forbidden, not_found, internal_error
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse
from app.schemas.response import BaseResponse, DataResponse, RoleOption
from typing import Optional, List
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


@router.get("/roles", tags=["員工管理"], response_model=DataResponse[List[RoleOption]])
async def list_roles_for_employees(
    current_user: CurrentUser = Depends(require_page_permission("employees.list"))
):
    """取得可指定的角色列表"""
    try:
        rows = await supabase_service.pool.fetch(
            "SELECT id, key, name FROM roles ORDER BY key"
        )
        return {"success": True, "message": "操作成功", "data": [{"id": str(r["id"]), "key": r["key"], "name": r["name"]} for r in rows]}
    except Exception as e:
        raise internal_error(f"取得角色列表失敗: {str(e)}", ErrorCode.EMPLOYEE_ROLES_LIST_FAILED)


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
        raise forbidden("僅限員工存取", ErrorCode.EMPLOYEE_FORBIDDEN_STAFF_ONLY)
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

        # 批次 enrich（取代 N+1 迴圈）
        if employees:
            emp_ids = [e["id"] for e in employees]
            pool = supabase_service.pool
            profile_rows = await pool.fetch(
                """SELECT up.employee_id, r.id AS role_id, r.name AS role_name
                   FROM user_profiles up
                   JOIN roles r ON r.id = up.role_id
                   WHERE up.employee_id = ANY($1)""",
                [__import__('uuid').UUID(eid) if isinstance(eid, str) else eid for eid in emp_ids],
            )
            profile_map = {str(r["employee_id"]): r for r in profile_rows}

            for emp in employees:
                p = profile_map.get(str(emp["id"]))
                emp["has_account"] = p is not None
                emp["role_id"] = str(p["role_id"]) if p else None
                emp["role_name"] = p["role_name"] if p else None

        return EmployeeListResponse(
            data=[EmployeeResponse(**emp) for emp in employees],
            total=total, page=page, per_page=per_page, total_pages=total_pages
        )
    except Exception as e:
        raise internal_error(f"取得員工列表失敗: {str(e)}", ErrorCode.EMPLOYEE_LIST_FAILED)


@router.get("/{employee_id}", response_model=DataResponse[EmployeeResponse])
async def get_employee(
    employee_id: str,
    current_user: CurrentUser = Depends(require_page_permission("employees.list"))
):
    """取得單一員工（僅限員工）"""
    if not current_user.is_staff():
        raise forbidden("僅限員工存取", ErrorCode.EMPLOYEE_FORBIDDEN_STAFF_ONLY)
    try:
        result = await supabase_service.table_select(
            table="employees", select=EMPLOYEE_SELECT,
            filters={"id": employee_id, "is_deleted": "eq.false"}
        )
        if not result:
            raise not_found("員工", ErrorCode.EMPLOYEE_NOT_FOUND)
        enriched = await enrich_employee(result[0])
        return DataResponse(data=EmployeeResponse(**enriched))
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"取得員工失敗: {str(e)}", ErrorCode.EMPLOYEE_GET_FAILED)


@router.post("", response_model=DataResponse[EmployeeResponse])
async def create_employee(
    data: EmployeeCreate,
    current_user: CurrentUser = Depends(require_page_permission("employees.create"))
):
    """建立員工（僅限管理員）"""
    if not current_user.is_admin():
        raise forbidden("僅限管理員操作", ErrorCode.EMPLOYEE_FORBIDDEN_ADMIN_ONLY)
    try:
        existing = await supabase_service.table_select(
            table="employees", select="id",
            filters={"employee_no": data.employee_no, "is_deleted": "eq.false"}
        )
        if existing:
            raise bad_request("員工編號已存在", ErrorCode.EMPLOYEE_NO_DUPLICATE)

        existing_email = await supabase_service.table_select(
            table="employees", select="id",
            filters={"email": data.email, "is_deleted": "eq.false"}
        )
        if existing_email:
            raise bad_request("此 Email 已被其他員工使用", ErrorCode.EMPLOYEE_EMAIL_USED_BY_EMPLOYEE)

        # 跨表檢查：員工 email 不可與學生或教師重複
        dup_student = await supabase_service.table_select(
            table="students", select="id",
            filters={"email": data.email, "is_deleted": "eq.false"}
        )
        if dup_student:
            raise bad_request("此 Email 已被學生使用", ErrorCode.EMPLOYEE_EMAIL_USED_BY_STUDENT)

        dup_teacher = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"email": data.email, "is_deleted": "eq.false"}
        )
        if dup_teacher:
            raise bad_request("此 Email 已被教師使用", ErrorCode.EMPLOYEE_EMAIL_USED_BY_TEACHER)

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
            raise internal_error("建立員工失敗", ErrorCode.EMPLOYEE_CREATE_FAILED)

        enriched = await enrich_employee(result)
        return DataResponse(message="員工建立成功", data=EmployeeResponse(**enriched))
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"建立員工失敗: {str(e)}", ErrorCode.EMPLOYEE_CREATE_FAILED)


@router.put("/{employee_id}", response_model=DataResponse[EmployeeResponse])
async def update_employee(
    employee_id: str,
    data: EmployeeUpdate,
    current_user: CurrentUser = Depends(require_page_permission("employees.edit"))
):
    """更新員工（僅限管理員）"""
    if not current_user.is_admin():
        raise forbidden("僅限管理員操作", ErrorCode.EMPLOYEE_FORBIDDEN_ADMIN_ONLY)
    try:
        existing = await supabase_service.table_select(
            table="employees", select="id,employee_no,email,employee_type",
            filters={"id": employee_id, "is_deleted": "eq.false"}
        )
        if not existing:
            raise not_found("員工", ErrorCode.EMPLOYEE_NOT_FOUND)

        if data.email and data.email != existing[0]["email"]:
            dup = await supabase_service.table_select(
                table="employees", select="id",
                filters={"email": data.email, "is_deleted": "eq.false"}
            )
            if dup:
                raise bad_request("此 Email 已被其他員工使用", ErrorCode.EMPLOYEE_EMAIL_USED_BY_EMPLOYEE)

            dup_student = await supabase_service.table_select(
                table="students", select="id",
                filters={"email": data.email, "is_deleted": "eq.false"}
            )
            if dup_student:
                raise bad_request("此 Email 已被學生使用", ErrorCode.EMPLOYEE_EMAIL_USED_BY_STUDENT)

            dup_teacher = await supabase_service.table_select(
                table="teachers", select="id",
                filters={"email": data.email, "is_deleted": "eq.false"}
            )
            if dup_teacher:
                raise bad_request("此 Email 已被教師使用", ErrorCode.EMPLOYEE_EMAIL_USED_BY_TEACHER)

        # role_id 不寫 employees 表，單獨處理
        requested_role_id = data.role_id
        employee_update = {k: v for k, v in data.model_dump().items() if v is not None}
        employee_update.pop("role_id", None)  # 不寫入 employees 表

        if "hire_date" in employee_update and employee_update["hire_date"]:
            employee_update["hire_date"] = employee_update["hire_date"].isoformat()
        if "termination_date" in employee_update and employee_update["termination_date"]:
            employee_update["termination_date"] = employee_update["termination_date"].isoformat()

        if not employee_update and not requested_role_id:
            raise bad_request("沒有要更新的資料", ErrorCode.EMPLOYEE_NO_UPDATE_DATA)

        result = existing[0]
        if employee_update:
            result = await supabase_service.table_update(
                table="employees", data=employee_update, filters={"id": employee_id}
            )
            if not result:
                raise internal_error("更新員工失敗", ErrorCode.EMPLOYEE_UPDATE_FAILED)

        # 同步 user_profiles 角色（僅限已有帳號的員工）
        profile = None
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
                if sync_data:
                    await supabase_service.table_update(
                        table="user_profiles",
                        data=sync_data,
                        filters={"id": profile[0]["id"]},
                    )
                    logger.info(f"Employee {employee_id}: user_profiles 同步 {sync_data}")
            elif requested_role_id:
                raise bad_request("此員工尚未建立帳號，無法設定角色", ErrorCode.EMPLOYEE_NO_ACCOUNT_FOR_ROLE)
        except Exception as sync_err:
            logger.warning(f"Employee {employee_id}: 同步角色失敗: {sync_err}")

        # 清除 Redis 權限快取，讓更改立即生效（不需重新登入）
        if profile:
            try:
                from app.services.redis_service import redis_service
                uid = profile[0]['id']
                await redis_service.delete(f"permission_level:{uid}")
                await redis_service.delete(f"role_id:{uid}")
                await redis_service.delete(f"employee_type:{uid}")
                await redis_service.delete(f"page_perm:{uid}")
            except Exception:
                pass

        enriched = await enrich_employee(result)
        return DataResponse(message="員工更新成功", data=EmployeeResponse(**enriched))
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"更新員工失敗: {str(e)}", ErrorCode.EMPLOYEE_UPDATE_FAILED)


@router.delete("/{employee_id}", response_model=BaseResponse)
async def delete_employee(
    employee_id: str,
    current_user: CurrentUser = Depends(require_page_permission("employees.delete"))
):
    """刪除員工（軟刪除，僅限管理員）"""
    if not current_user.is_admin():
        raise forbidden("僅限管理員操作", ErrorCode.EMPLOYEE_FORBIDDEN_ADMIN_ONLY)
    try:
        existing = await supabase_service.table_select(
            table="employees", select="id",
            filters={"id": employee_id, "is_deleted": "eq.false"}
        )
        if not existing:
            raise not_found("員工", ErrorCode.EMPLOYEE_NOT_FOUND)

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
            raise internal_error("刪除員工失敗", ErrorCode.EMPLOYEE_DELETE_FAILED)

        return BaseResponse(message="員工刪除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"刪除員工失敗: {str(e)}", ErrorCode.EMPLOYEE_DELETE_FAILED)
