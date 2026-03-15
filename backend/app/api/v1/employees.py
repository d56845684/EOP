from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_page_permission, get_user_employee_id
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeListResponse
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime
import math

router = APIRouter(prefix="/employees", tags=["員工管理"])

EMPLOYEE_SELECT = "id,employee_no,employee_type,name,email,phone,address,hire_date,termination_date,is_active,created_at,updated_at"


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

        all_employees = await supabase_service.table_select(
            table="employees", select="id", filters=filters
        )
        total = len(all_employees)
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
        return DataResponse(data=EmployeeResponse(**result[0]))
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

        return DataResponse(message="員工建立成功", data=EmployeeResponse(**result))
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
            table="employees", select="id,employee_no,email",
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

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if "hire_date" in update_data and update_data["hire_date"]:
            update_data["hire_date"] = update_data["hire_date"].isoformat()
        if "termination_date" in update_data and update_data["termination_date"]:
            update_data["termination_date"] = update_data["termination_date"].isoformat()

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="employees", data=update_data, filters={"id": employee_id}
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新員工失敗")

        return DataResponse(message="員工更新成功", data=EmployeeResponse(**result))
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
