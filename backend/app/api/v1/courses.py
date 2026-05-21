from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_page_permission, get_user_employee_id
from app.core.error_codes import ErrorCode
from app.core.exceptions import bad_request, not_found, internal_error
from app.schemas.course import (
    CourseCreate, CourseUpdate, CourseResponse, CourseListResponse
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
import math
import uuid

router = APIRouter(prefix="/courses", tags=["課程管理"])


async def _count_active_teacher_contract_details_for_course(course_id: str) -> int:
    """計算課程被多少 active 教師合約明細引用。

    用於刪除 / 停用課程前的硬擋檢查

    Active reference 定義：
    - teacher_contract_details.is_deleted = FALSE
    - teacher_contracts.is_deleted = FALSE
    - teacher_contracts.contract_status = 'active'

    其他狀態（pending / expired / terminated / suspended）的合約不算 active
    引用，視為歷史紀錄，允許課程刪除 / 停用。
    """
    return await supabase_service.pool.fetchval(
        """SELECT COUNT(*)
           FROM teacher_contract_details d
           JOIN teacher_contracts c ON c.id = d.teacher_contract_id
           WHERE d.course_id = $1
             AND d.is_deleted = FALSE
             AND c.is_deleted = FALSE
             AND c.contract_status = 'active'""",
        uuid.UUID(course_id),
    )


@router.get("", response_model=CourseListResponse)
async def list_courses(
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(20, ge=1, le=100, description="每頁數量"),
    search: Optional[str] = Query(None, description="搜尋關鍵字（課程代碼或名稱）"),
    is_active: Optional[bool] = Query(None, description="篩選啟用狀態"),
    current_user: CurrentUser = Depends(require_page_permission("courses.list"))
):
    """取得課程列表"""
    try:
        # 建立基本查詢
        filters = {"is_deleted": "eq.false"}

        if is_active is not None:
            filters["is_active"] = f"eq.{str(is_active).lower()}"

        # 取得總數
        total = await supabase_service.table_count(table="courses", filters=filters)

        # 計算分頁
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        # 取得分頁資料
        courses = await supabase_service.table_select_with_pagination(
            table="courses",
            select="id,course_code,course_name,description,duration_minutes,is_active,created_at,updated_at",
            filters=filters,
            order_by="created_at.desc",
            limit=per_page,
            offset=offset,
        )

        # 如果有搜尋關鍵字，在結果中篩選（PostgREST 的 or 較複雜，這裡簡化處理）
        if search:
            search_lower = search.lower()
            courses = [
                c for c in courses
                if search_lower in c.get("course_code", "").lower()
                or search_lower in c.get("course_name", "").lower()
            ]

        return CourseListResponse(
            data=[CourseResponse(**c) for c in courses],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        raise internal_error(f"取得課程列表失敗: {str(e)}", ErrorCode.COURSE_LIST_FAILED)


@router.get("/{course_id}", response_model=DataResponse[CourseResponse])
async def get_course(
    course_id: str,
    current_user: CurrentUser = Depends(require_page_permission("courses.list"))
):
    """取得單一課程"""
    try:
        result = await supabase_service.table_select(
            table="courses",
            select="id,course_code,course_name,description,duration_minutes,is_active,created_at,updated_at",
            filters={"id": course_id, "is_deleted": "eq.false"},
        )

        if not result:
            raise not_found("課程", ErrorCode.COURSE_NOT_FOUND)

        return DataResponse(data=CourseResponse(**result[0]))

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"取得課程失敗: {str(e)}", ErrorCode.COURSE_GET_FAILED)


@router.post("", response_model=DataResponse[CourseResponse])
async def create_course(
    data: CourseCreate,
    current_user: CurrentUser = Depends(require_page_permission("courses.create"))
):
    """建立課程（僅限員工）"""
    try:
        # 檢查課程代碼是否已存在
        existing = await supabase_service.table_select(
            table="courses",
            select="id",
            filters={"course_code": data.course_code, "is_deleted": "eq.false"},
        )

        if existing:
            raise bad_request("課程代碼已存在", ErrorCode.COURSE_DUPLICATE_CODE)

        # 建立課程
        course_data = data.model_dump()

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            course_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="courses",
            data=course_data,
        )

        if not result:
            raise internal_error("建立課程失敗", ErrorCode.COURSE_CREATE_FAILED)

        # table_insert 返回單個 dict 而不是 list
        return DataResponse(
            message="課程建立成功",
            data=CourseResponse(**result)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"建立課程失敗: {str(e)}", ErrorCode.COURSE_CREATE_FAILED)


@router.put("/{course_id}", response_model=DataResponse[CourseResponse])
async def update_course(
    course_id: str,
    data: CourseUpdate,
    current_user: CurrentUser = Depends(require_page_permission("courses.edit"))
):
    """更新課程（僅限員工）"""
    try:
        # 檢查課程是否存在
        existing = await supabase_service.table_select(
            table="courses",
            select="id,course_code",
            filters={"id": course_id, "is_deleted": "eq.false"},
        )

        if not existing:
            raise not_found("課程", ErrorCode.COURSE_NOT_FOUND)

        # 如果更新課程代碼，檢查是否重複
        if data.course_code and data.course_code != existing[0]["course_code"]:
            duplicate = await supabase_service.table_select(
                table="courses",
                select="id",
                filters={"course_code": data.course_code, "is_deleted": "eq.false"},
            )
            if duplicate:
                raise bad_request("課程代碼已存在", ErrorCode.COURSE_DUPLICATE_CODE)

        # 更新課程
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}

        if not update_data:
            raise bad_request("沒有要更新的資料", ErrorCode.COURSE_NO_UPDATE_DATA)

        # 停用課程（is_active=False）若仍有 active 教師合約引用，硬擋
        if update_data.get("is_active") is False:
            ref_count = await _count_active_teacher_contract_details_for_course(course_id)
            if ref_count > 0:
                raise bad_request((
                        f"該課程仍在 {ref_count} 份 active 教師合約明細中使用，"
                        "無法停用。請先在合約明細中移除此課程。"
                    ), ErrorCode.COURSE_INTERNAL_400)

        result = await supabase_service.table_update(
            table="courses",
            data=update_data,
            filters={"id": course_id},
        )

        if not result:
            raise internal_error("更新課程失敗", ErrorCode.COURSE_UPDATE_FAILED)

        # table_update 返回單個 dict 而不是 list
        return DataResponse(
            message="課程更新成功",
            data=CourseResponse(**result)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"更新課程失敗: {str(e)}", ErrorCode.COURSE_UPDATE_FAILED)


@router.delete("/{course_id}", response_model=BaseResponse)
async def delete_course(
    course_id: str,
    current_user: CurrentUser = Depends(require_page_permission("courses.delete"))
):
    """刪除課程（軟刪除，僅限員工）。

    若仍有 active 教師合約明細引用，硬擋並提示員工先去合約清掉。
    """
    try:
        # 檢查課程是否存在
        existing = await supabase_service.table_select(
            table="courses",
            select="id",
            filters={"id": course_id, "is_deleted": "eq.false"},
        )

        if not existing:
            raise not_found("課程", ErrorCode.COURSE_NOT_FOUND)

        # 硬擋：仍被 active 教師合約明細引用
        ref_count = await _count_active_teacher_contract_details_for_course(course_id)
        if ref_count > 0:
            raise bad_request((
                    f"該課程仍在 {ref_count} 份 active 教師合約明細中使用，"
                    "無法刪除。請先在合約明細中移除此課程。"
                ), ErrorCode.COURSE_INTERNAL_400)

        # 軟刪除
        from datetime import datetime
        result = await supabase_service.table_update(
            table="courses",
            data={
                "is_deleted": True,
                "deleted_at": datetime.utcnow().isoformat()
            },
            filters={"id": course_id},
        )

        if not result:
            raise internal_error("刪除課程失敗", ErrorCode.COURSE_DELETE_FAILED)

        return BaseResponse(message="課程刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"刪除課程失敗: {str(e)}", ErrorCode.COURSE_DELETE_FAILED)
