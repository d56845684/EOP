from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, get_user_employee_id
from app.schemas.student_teacher_preference import (
    StudentTeacherPreferenceCreate, StudentTeacherPreferenceUpdate, StudentTeacherPreferenceResponse
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional

router = APIRouter(prefix="/student-teacher-preferences", tags=["學生教師偏好"])

PREF_SELECT = "id,student_id,course_id,min_teacher_level,primary_teacher_id,created_at,updated_at"


async def enrich_preference(pref: dict) -> dict:
    """補充偏好的關聯名稱"""
    # 學生名稱
    if pref.get("student_id"):
        student = await supabase_service.table_select(
            table="students", select="name",
            filters={"id": pref["student_id"]},
        )
        pref["student_name"] = student[0]["name"] if student else None

    # 課程名稱
    if pref.get("course_id"):
        course = await supabase_service.table_select(
            table="courses", select="course_name",
            filters={"id": pref["course_id"]},
        )
        pref["course_name"] = course[0]["course_name"] if course else None
    else:
        pref["course_name"] = None

    # 主要教師名稱
    if pref.get("primary_teacher_id"):
        teacher = await supabase_service.table_select(
            table="teachers", select="name",
            filters={"id": pref["primary_teacher_id"]},
        )
        pref["primary_teacher_name"] = teacher[0]["name"] if teacher else None
    else:
        pref["primary_teacher_name"] = None

    return pref


@router.get("/", tags=["學生教師偏好"])
async def list_preferences(
    student_id: str = Query(..., description="學生 ID"),
    current_user: CurrentUser = Depends(get_current_user)
):
    """列出學生的教師偏好設定"""
    try:
        prefs = await supabase_service.table_select(
            table="student_teacher_preferences",
            select=PREF_SELECT,
            filters={
                "student_id": student_id,
                "is_deleted": "eq.false"
            },
        )

        enriched = []
        for p in prefs:
            enriched.append(await enrich_preference(p))

        return {"success": True, "data": enriched}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=DataResponse[StudentTeacherPreferenceResponse])
async def create_preference(
    data: StudentTeacherPreferenceCreate,
    current_user: CurrentUser = Depends(require_staff)
):
    """新增學生教師偏好（僅員工）"""
    try:
        employee_id = await get_user_employee_id(current_user.user_id)

        # 驗證學生存在
        student = await supabase_service.table_select(
            table="students", select="id",
            filters={"id": data.student_id, "is_deleted": "eq.false"},
        )
        if not student:
            raise HTTPException(status_code=400, detail="學生不存在")

        # 驗證課程存在（如果有提供）
        if data.course_id:
            course = await supabase_service.table_select(
                table="courses", select="id",
                filters={"id": data.course_id, "is_deleted": "eq.false"},
            )
            if not course:
                raise HTTPException(status_code=400, detail="課程不存在")

        # 驗證主要教師存在（如果有提供）
        if data.primary_teacher_id:
            teacher = await supabase_service.table_select(
                table="teachers", select="id",
                filters={"id": data.primary_teacher_id, "is_deleted": "eq.false"},
            )
            if not teacher:
                raise HTTPException(status_code=400, detail="主要教師不存在")

        # 檢查唯一性
        if data.primary_teacher_id:
            # 指定教師模式：同學生+同教師不能重複
            dup_filters = {
                "student_id": data.student_id,
                "primary_teacher_id": data.primary_teacher_id,
                "is_deleted": "eq.false"
            }
            existing = await supabase_service.table_select(
                table="student_teacher_preferences",
                select="id",
                filters=dup_filters,
            )
            if existing:
                raise HTTPException(status_code=400, detail="此學生已指定該教師，請編輯現有設定")
        else:
            # 等級模式：同學生+同課程（含全域）不能重複
            dup_filters = {
                "student_id": data.student_id,
                "primary_teacher_id": "is.null",
                "is_deleted": "eq.false"
            }
            if data.course_id:
                dup_filters["course_id"] = data.course_id
            else:
                dup_filters["course_id"] = "is.null"

            existing = await supabase_service.table_select(
                table="student_teacher_preferences",
                select="id",
                filters=dup_filters,
            )
            if existing:
                scope = "全域" if not data.course_id else "該課程"
                raise HTTPException(status_code=400, detail=f"此學生已有{scope}等級偏好設定，請編輯現有設定")

        insert_data = {
            "student_id": data.student_id,
            "course_id": data.course_id,
            "min_teacher_level": data.min_teacher_level,
            "primary_teacher_id": data.primary_teacher_id,
        }
        if employee_id:
            insert_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="student_teacher_preferences",
            data=insert_data,
        )

        if not result:
            raise HTTPException(status_code=500, detail="建立偏好失敗")

        enriched = await enrich_preference(result)

        return DataResponse(
            message="偏好建立成功",
            data=StudentTeacherPreferenceResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立偏好失敗: {str(e)}")


@router.put("/{preference_id}", response_model=DataResponse[StudentTeacherPreferenceResponse])
async def update_preference(
    preference_id: str,
    data: StudentTeacherPreferenceUpdate,
    current_user: CurrentUser = Depends(require_staff)
):
    """更新學生教師偏好（僅員工）"""
    try:
        employee_id = await get_user_employee_id(current_user.user_id)

        # 驗證偏好存在
        existing = await supabase_service.table_select(
            table="student_teacher_preferences",
            select=PREF_SELECT,
            filters={"id": preference_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="偏好設定不存在")

        # 驗證主要教師存在（如果有提供）
        if data.primary_teacher_id:
            teacher = await supabase_service.table_select(
                table="teachers", select="id",
                filters={"id": data.primary_teacher_id, "is_deleted": "eq.false"},
            )
            if not teacher:
                raise HTTPException(status_code=400, detail="主要教師不存在")

        update_data = {}
        # 使用 model_fields_set 判斷前端是否有明確傳入該欄位（包含 null）
        if "min_teacher_level" in data.model_fields_set:
            update_data["min_teacher_level"] = data.min_teacher_level
        if "primary_teacher_id" in data.model_fields_set:
            update_data["primary_teacher_id"] = data.primary_teacher_id

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有需要更新的欄位")

        if employee_id:
            update_data["updated_by"] = employee_id

        result = await supabase_service.table_update(
            table="student_teacher_preferences",
            data=update_data,
            filters={"id": preference_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新偏好失敗")

        enriched = await enrich_preference(result)

        return DataResponse(
            message="偏好更新成功",
            data=StudentTeacherPreferenceResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新偏好失敗: {str(e)}")


@router.delete("/{preference_id}", response_model=BaseResponse)
async def delete_preference(
    preference_id: str,
    current_user: CurrentUser = Depends(require_staff)
):
    """軟刪除學生教師偏好（僅員工）"""
    try:
        employee_id = await get_user_employee_id(current_user.user_id)

        # 驗證偏好存在
        existing = await supabase_service.table_select(
            table="student_teacher_preferences",
            select="id",
            filters={"id": preference_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="偏好設定不存在")

        delete_data = {
            "is_deleted": True,
            "deleted_at": "now()",
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        await supabase_service.table_update(
            table="student_teacher_preferences",
            data=delete_data,
            filters={"id": preference_id},
        )

        return BaseResponse(message="偏好刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除偏好失敗: {str(e)}")
