from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, get_user_employee_id
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse, StudentListResponse
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime
import math

router = APIRouter(prefix="/students", tags=["學生管理"])

STUDENT_SELECT = "id,student_no,name,email,phone,address,birth_date,student_type,is_active,created_at,updated_at"


@router.get("", response_model=StudentListResponse)
async def list_students(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜尋（編號/姓名/email）"),
    is_active: Optional[bool] = Query(None),
    student_type: Optional[str] = Query(None, description="學生類型 (formal/trial)"),
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得學生列表"""
    try:
        filters = {"is_deleted": "eq.false"}
        if is_active is not None:
            filters["is_active"] = f"eq.{str(is_active).lower()}"
        if student_type:
            filters["student_type"] = f"eq.{student_type}"

        all_students = await supabase_service.table_select(
            table="students", select="id", filters=filters, use_service_key=True
        )
        total = len(all_students)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        students = await supabase_service.table_select_with_pagination(
            table="students", select=STUDENT_SELECT, filters=filters,
            order_by="created_at.desc", limit=per_page, offset=offset, use_service_key=True
        )

        if search:
            s = search.lower()
            students = [
                st for st in students
                if s in st.get("student_no", "").lower()
                or s in st.get("name", "").lower()
                or s in st.get("email", "").lower()
            ]

        return StudentListResponse(
            data=[StudentResponse(**st) for st in students],
            total=total, page=page, per_page=per_page, total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得學生列表失敗: {str(e)}")


@router.get("/{student_id}", response_model=DataResponse[StudentResponse])
async def get_student(
    student_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得單一學生"""
    try:
        result = await supabase_service.table_select(
            table="students", select=STUDENT_SELECT,
            filters={"id": student_id, "is_deleted": "eq.false"}, use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="學生不存在")
        return DataResponse(data=StudentResponse(**result[0]))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得學生失敗: {str(e)}")


@router.post("", response_model=DataResponse[StudentResponse])
async def create_student(
    data: StudentCreate,
    current_user: CurrentUser = Depends(require_staff)
):
    """建立學生（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="students", select="id",
            filters={"student_no": data.student_no, "is_deleted": "eq.false"}, use_service_key=True
        )
        if existing:
            raise HTTPException(status_code=400, detail="學生編號已存在")

        existing_email = await supabase_service.table_select(
            table="students", select="id",
            filters={"email": data.email, "is_deleted": "eq.false"}, use_service_key=True
        )
        if existing_email:
            raise HTTPException(status_code=400, detail="Email 已存在")

        student_data = data.model_dump()
        if student_data.get("birth_date"):
            student_data["birth_date"] = student_data["birth_date"].isoformat()

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            student_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="students", data=student_data, use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=500, detail="建立學生失敗")

        return DataResponse(message="學生建立成功", data=StudentResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立學生失敗: {str(e)}")


@router.put("/{student_id}", response_model=DataResponse[StudentResponse])
async def update_student(
    student_id: str,
    data: StudentUpdate,
    current_user: CurrentUser = Depends(require_staff)
):
    """更新學生（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="students", select="id,student_no,email",
            filters={"id": student_id, "is_deleted": "eq.false"}, use_service_key=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="學生不存在")

        if data.email and data.email != existing[0]["email"]:
            dup = await supabase_service.table_select(
                table="students", select="id",
                filters={"email": data.email, "is_deleted": "eq.false"}, use_service_key=True
            )
            if dup:
                raise HTTPException(status_code=400, detail="Email 已存在")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if "birth_date" in update_data and update_data["birth_date"]:
            update_data["birth_date"] = update_data["birth_date"].isoformat()

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="students", data=update_data, filters={"id": student_id}, use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新學生失敗")

        return DataResponse(message="學生更新成功", data=StudentResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新學生失敗: {str(e)}")


@router.delete("/{student_id}", response_model=BaseResponse)
async def delete_student(
    student_id: str,
    current_user: CurrentUser = Depends(require_staff)
):
    """刪除學生（軟刪除，僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="students", select="id",
            filters={"id": student_id, "is_deleted": "eq.false"}, use_service_key=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="學生不存在")

        result = await supabase_service.table_update(
            table="students",
            data={"is_deleted": True, "deleted_at": datetime.utcnow().isoformat()},
            filters={"id": student_id}, use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=500, detail="刪除學生失敗")

        return BaseResponse(message="學生刪除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除學生失敗: {str(e)}")
