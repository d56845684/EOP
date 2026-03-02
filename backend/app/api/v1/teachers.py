from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, get_user_employee_id
from app.schemas.teacher import TeacherCreate, TeacherUpdate, TeacherResponse, TeacherListResponse
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime
import math

router = APIRouter(prefix="/teachers", tags=["教師管理"])

TEACHER_SELECT = "id,teacher_no,name,email,phone,address,bio,teacher_level,is_active,created_at,updated_at"


@router.get("", response_model=TeacherListResponse)
async def list_teachers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜尋（編號/姓名/email）"),
    is_active: Optional[bool] = Query(None),
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得教師列表"""
    try:
        filters = {"is_deleted": "eq.false"}
        if is_active is not None:
            filters["is_active"] = f"eq.{str(is_active).lower()}"

        all_teachers = await supabase_service.table_select(
            table="teachers", select="id", filters=filters, use_service_key=True
        )
        total = len(all_teachers)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        teachers = await supabase_service.table_select_with_pagination(
            table="teachers", select=TEACHER_SELECT, filters=filters,
            order_by="created_at.desc", limit=per_page, offset=offset, use_service_key=True
        )

        if search:
            s = search.lower()
            teachers = [
                t for t in teachers
                if s in t.get("teacher_no", "").lower()
                or s in t.get("name", "").lower()
                or s in t.get("email", "").lower()
            ]

        return TeacherListResponse(
            data=[TeacherResponse(**t) for t in teachers],
            total=total, page=page, per_page=per_page, total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師列表失敗: {str(e)}")


@router.get("/{teacher_id}", response_model=DataResponse[TeacherResponse])
async def get_teacher(
    teacher_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得單一教師"""
    try:
        result = await supabase_service.table_select(
            table="teachers", select=TEACHER_SELECT,
            filters={"id": teacher_id, "is_deleted": "eq.false"}, use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=404, detail="教師不存在")
        return DataResponse(data=TeacherResponse(**result[0]))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師失敗: {str(e)}")


@router.post("", response_model=DataResponse[TeacherResponse])
async def create_teacher(
    data: TeacherCreate,
    current_user: CurrentUser = Depends(require_staff)
):
    """建立教師（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"teacher_no": data.teacher_no, "is_deleted": "eq.false"}, use_service_key=True
        )
        if existing:
            raise HTTPException(status_code=400, detail="教師編號已存在")

        existing_email = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"email": data.email, "is_deleted": "eq.false"}, use_service_key=True
        )
        if existing_email:
            raise HTTPException(status_code=400, detail="Email 已存在")

        teacher_data = data.model_dump()
        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            teacher_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="teachers", data=teacher_data, use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=500, detail="建立教師失敗")

        return DataResponse(message="教師建立成功", data=TeacherResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立教師失敗: {str(e)}")


@router.put("/{teacher_id}", response_model=DataResponse[TeacherResponse])
async def update_teacher(
    teacher_id: str,
    data: TeacherUpdate,
    current_user: CurrentUser = Depends(require_staff)
):
    """更新教師（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teachers", select="id,teacher_no,email",
            filters={"id": teacher_id, "is_deleted": "eq.false"}, use_service_key=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師不存在")

        if data.email and data.email != existing[0]["email"]:
            dup = await supabase_service.table_select(
                table="teachers", select="id",
                filters={"email": data.email, "is_deleted": "eq.false"}, use_service_key=True
            )
            if dup:
                raise HTTPException(status_code=400, detail="Email 已存在")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="teachers", data=update_data, filters={"id": teacher_id}, use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新教師失敗")

        return DataResponse(message="教師更新成功", data=TeacherResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新教師失敗: {str(e)}")


@router.delete("/{teacher_id}", response_model=BaseResponse)
async def delete_teacher(
    teacher_id: str,
    current_user: CurrentUser = Depends(require_staff)
):
    """刪除教師（軟刪除，僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"id": teacher_id, "is_deleted": "eq.false"}, use_service_key=True
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師不存在")

        result = await supabase_service.table_update(
            table="teachers",
            data={"is_deleted": True, "deleted_at": datetime.utcnow().isoformat()},
            filters={"id": teacher_id}, use_service_key=True
        )
        if not result:
            raise HTTPException(status_code=500, detail="刪除教師失敗")

        return BaseResponse(message="教師刪除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除教師失敗: {str(e)}")
