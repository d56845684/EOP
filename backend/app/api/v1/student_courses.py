from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_page_permission, get_user_employee_id
from app.schemas.student_course import (
    StudentCourseCreate, StudentCourseResponse, StudentCourseListResponse
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime
import math

router = APIRouter(prefix="/student-courses", tags=["學生選課管理"])

ENROLLMENT_SELECT = "id,student_id,course_id,enrolled_at,created_at"


async def enrich_enrollment(enrollment: dict) -> dict:
    """為選課資料添加課程和學生名稱"""
    if enrollment.get("course_id"):
        course = await supabase_service.table_select(
            table="courses",
            select="course_code,course_name",
            filters={"id": enrollment["course_id"]},
        )
        if course:
            enrollment["course_code"] = course[0].get("course_code")
            enrollment["course_name"] = course[0].get("course_name")

    if enrollment.get("student_id"):
        student = await supabase_service.table_select(
            table="students",
            select="name",
            filters={"id": enrollment["student_id"]},
        )
        if student:
            enrollment["student_name"] = student[0].get("name")

    return enrollment


# ========== Options ==========

@router.get("/options/students", tags=["學生選課管理"])
async def get_student_options(
    current_user: CurrentUser = Depends(require_page_permission("students.courses"))
):
    """取得學生下拉選單"""
    try:
        students = await supabase_service.table_select(
            table="students",
            select="id,student_no,name",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        return {"data": students}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/courses", tags=["學生選課管理"])
async def get_course_options(
    current_user: CurrentUser = Depends(require_page_permission("students.courses"))
):
    """取得課程下拉選單"""
    try:
        courses = await supabase_service.table_select(
            table="courses",
            select="id,course_code,course_name",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        return {"data": courses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== CRUD ==========

@router.get("", response_model=StudentCourseListResponse)
async def list_student_courses(
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(20, ge=1, le=100, description="每頁數量"),
    student_id: Optional[str] = Query(None, description="篩選學生"),
    search: Optional[str] = Query(None, description="搜尋課程名稱"),
    current_user: CurrentUser = Depends(require_page_permission("students.courses"))
):
    """取得學生選課列表

    權限控制:
    - 學生: 僅能看到自己的選課
    - 教師: 無法查看
    - 員工/管理員: 可查看所有選課
    """
    try:
        filters = {"is_deleted": "eq.false"}

        if current_user.is_student():
            user_student_id = current_user.student_id
            if not user_student_id:
                return StudentCourseListResponse(data=[], total=0, page=page, per_page=per_page, total_pages=1)
            filters["student_id"] = f"eq.{user_student_id}"
        elif current_user.is_teacher():
            return StudentCourseListResponse(data=[], total=0, page=page, per_page=per_page, total_pages=1)

        if student_id and not current_user.is_student():
            filters["student_id"] = f"eq.{student_id}"

        # Get total count
        all_enrollments = await supabase_service.table_select(
            table="student_courses",
            select="id",
            filters=filters,
        )
        total = len(all_enrollments)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        # Get paginated data
        enrollments = await supabase_service.table_select_with_pagination(
            table="student_courses",
            select=ENROLLMENT_SELECT,
            filters=filters,
            order_by="created_at.desc",
            limit=per_page,
            offset=offset,
        )

        # Enrich with names
        enriched = []
        for e in enrollments:
            enriched.append(await enrich_enrollment(e))

        # Search filter (post-query)
        if search:
            search_lower = search.lower()
            enriched = [
                e for e in enriched
                if search_lower in (e.get("course_name") or "").lower()
                or search_lower in (e.get("student_name") or "").lower()
                or search_lower in (e.get("course_code") or "").lower()
            ]

        return StudentCourseListResponse(
            data=[StudentCourseResponse(**e) for e in enriched],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得學生選課列表失敗: {str(e)}")


@router.get("/by-student/{student_id}")
async def get_courses_by_student(
    student_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.courses"))
):
    """取得某學生的已選課程（供合約明細 course 下拉用）"""
    try:
        # Ownership check: 學生只能查自己的選課
        if current_user.is_student():
            user_student_id = current_user.student_id
            if student_id != user_student_id:
                raise HTTPException(status_code=403, detail="無權查看其他學生的選課")

        enrollments = await supabase_service.table_select(
            table="student_courses",
            select=ENROLLMENT_SELECT,
            filters={
                "student_id": f"eq.{student_id}",
                "is_deleted": "eq.false"
            },
        )

        enriched = []
        for e in enrollments:
            enriched.append(await enrich_enrollment(e))

        return {"data": enriched}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得學生選課失敗: {str(e)}")


@router.post("", response_model=DataResponse[StudentCourseResponse])
async def create_student_course(
    data: StudentCourseCreate,
    current_user: CurrentUser = Depends(require_page_permission("students.edit"))
):
    """新增學生選課（僅限員工）"""
    try:
        # 驗證學生存在
        student = await supabase_service.table_select(
            table="students",
            select="id,name",
            filters={"id": data.student_id, "is_deleted": "eq.false"},
        )
        if not student:
            raise HTTPException(status_code=400, detail="學生不存在")

        # 驗證課程存在
        course = await supabase_service.table_select(
            table="courses",
            select="id,course_code,course_name",
            filters={"id": data.course_id, "is_deleted": "eq.false"},
        )
        if not course:
            raise HTTPException(status_code=400, detail="課程不存在")

        # 檢查是否已存在（未刪除）
        existing = await supabase_service.table_select(
            table="student_courses",
            select="id",
            filters={
                "student_id": f"eq.{data.student_id}",
                "course_id": f"eq.{data.course_id}",
                "is_deleted": "eq.false"
            },
        )
        if existing:
            raise HTTPException(status_code=400, detail="此學生已選修此課程")

        enrollment_data = {
            "student_id": data.student_id,
            "course_id": data.course_id,
        }

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            enrollment_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="student_courses",
            data=enrollment_data,
        )

        if not result:
            raise HTTPException(status_code=500, detail="新增學生選課失敗")

        enriched = await enrich_enrollment(result)

        return DataResponse(
            message="學生選課新增成功",
            data=StudentCourseResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新增學生選課失敗: {str(e)}")


@router.delete("/{enrollment_id}", response_model=BaseResponse)
async def delete_student_course(
    enrollment_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.edit"))
):
    """移除學生選課（軟刪除，僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="student_courses",
            select="id",
            filters={"id": enrollment_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="選課紀錄不存在")

        employee_id = await get_user_employee_id(current_user.user_id)
        now = datetime.utcnow().isoformat()

        delete_data = {
            "is_deleted": True,
            "deleted_at": now
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        result = await supabase_service.table_update(
            table="student_courses",
            data=delete_data,
            filters={"id": enrollment_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="移除學生選課失敗")

        return BaseResponse(message="學生選課移除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"移除學生選課失敗: {str(e)}")
