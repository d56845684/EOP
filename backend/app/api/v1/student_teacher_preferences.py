from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.services.preference_service import preference_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_page_permission, get_user_employee_id
from app.schemas.student_teacher_preference import (
    StudentTeacherPreferenceCreate,
    StudentTeacherPreferenceUpdate, StudentTeacherPreferenceResponse
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional, List

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


@router.get("/options/teachers", tags=["學生教師偏好"])
async def get_teacher_options(
    current_user: CurrentUser = Depends(require_page_permission("students.edit"))
):
    """取得所有教師選項（偏好管理用下拉選單）"""
    try:
        teachers = await supabase_service.table_select(
            table="teachers",
            select="id,teacher_no,name,teacher_level",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        return {"success": True, "message": "操作成功", "data": teachers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/courses", tags=["學生教師偏好"])
async def get_course_options(
    student_id: str = Query(..., description="學生 ID"),
    current_user: CurrentUser = Depends(require_page_permission("students.edit"))
):
    """取得學生已選課程選項（偏好管理用下拉選單）"""
    try:
        # 查詢學生選課
        student_courses = await supabase_service.table_select(
            table="student_courses",
            select="course_id",
            filters={"student_id": student_id, "is_deleted": "eq.false"},
        )
        if not student_courses:
            return {"success": True, "message": "操作成功", "data": []}

        course_ids = [sc["course_id"] for sc in student_courses if sc.get("course_id")]
        if not course_ids:
            return {"success": True, "message": "操作成功", "data": []}

        # 查詢課程詳情
        pool = supabase_service.pool
        courses = await pool.fetch(
            "SELECT id, course_name FROM courses WHERE id = ANY($1) AND is_deleted = FALSE",
            course_ids,
        )
        return {"success": True, "message": "操作成功", "data": [dict(c) for c in courses]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allowed-teachers", tags=["學生教師偏好"])
async def get_allowed_teachers(
    student_id: str = Query(..., description="學生 ID"),
    current_user: CurrentUser = Depends(require_page_permission("students.edit"))
):
    """取得學生偏好設定的可預約教師白名單（完整資料）"""
    try:
        allowed_set, has_preferences = await preference_service.get_student_allowed_teachers(student_id)

        if not has_preferences:
            return {"success": True, "message": "操作成功", "data": []}

        # 查詢白名單內的教師完整資料
        teachers = await supabase_service.table_select(
            table="teachers",
            select="id,teacher_no,name,teacher_level",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        filtered = [t for t in teachers if str(t["id"]) in allowed_set]

        return {"success": True, "message": "操作成功", "data": filtered}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", tags=["學生教師偏好"])
async def list_preferences(
    student_id: str = Query(..., description="學生 ID"),
    current_user: CurrentUser = Depends(require_page_permission("students.edit"))
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

        # 批次 enrich（取代 N+1 迴圈）
        if prefs:
            s_ids = list({p["student_id"] for p in prefs if p.get("student_id")})
            c_ids = list({p["course_id"] for p in prefs if p.get("course_id")})
            t_ids = list({p["primary_teacher_id"] for p in prefs if p.get("primary_teacher_id")})
            pool = supabase_service.pool

            import asyncio as _aio
            async def _empty(): return []

            s_task = pool.fetch("SELECT id, name FROM students WHERE id = ANY($1)", s_ids) if s_ids else _empty()
            c_task = pool.fetch("SELECT id, course_name FROM courses WHERE id = ANY($1)", c_ids) if c_ids else _empty()
            t_task = pool.fetch("SELECT id, name FROM teachers WHERE id = ANY($1)", t_ids) if t_ids else _empty()

            s_rows, c_rows, t_rows = await _aio.gather(s_task, c_task, t_task)
            s_map = {str(r["id"]): r["name"] for r in s_rows}
            c_map = {str(r["id"]): r["course_name"] for r in c_rows}
            t_map = {str(r["id"]): r["name"] for r in t_rows}

            for p in prefs:
                p["student_name"] = s_map.get(str(p.get("student_id")))
                p["course_name"] = c_map.get(str(p.get("course_id")))
                p["primary_teacher_name"] = t_map.get(str(p.get("primary_teacher_id")))

        return {"success": True, "message": "操作成功", "data": prefs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_preference(
    data: StudentTeacherPreferenceCreate,
    current_user: CurrentUser = Depends(require_page_permission("students.edit"))
):
    """新增學生教師偏好（僅員工）

    - 傳 primary_teacher_ids（1 筆）→ 單筆建立
    - 傳 primary_teacher_ids（多筆）→ 批次建立（自動跳過重複）
    - 不傳 primary_teacher_ids（只傳 min_teacher_level）→ 等級模式
    """
    try:
        employee_id = await get_user_employee_id(current_user.user_id)

        # 驗證學生存在
        student = await supabase_service.table_select(
            table="students", select="id",
            filters={"id": data.student_id, "is_deleted": "eq.false"},
        )
        if not student:
            raise HTTPException(status_code=400, detail="學生不存在")

        # ── 指定教師模式（單筆 or 批次） ──
        if data.primary_teacher_ids:
            pool = supabase_service.pool

            # 驗證所有教師存在
            teacher_rows = await pool.fetch(
                "SELECT id FROM teachers WHERE id = ANY($1) AND is_deleted = false",
                list(data.primary_teacher_ids),
            )
            valid_ids = {str(r["id"]) for r in teacher_rows}
            invalid_ids = set(data.primary_teacher_ids) - valid_ids
            if invalid_ids:
                raise HTTPException(status_code=400, detail=f"以下教師不存在: {', '.join(invalid_ids)}")

            # 查出已存在的偏好（避免重複）
            existing = await pool.fetch(
                "SELECT primary_teacher_id FROM student_teacher_preferences "
                "WHERE student_id = $1 AND primary_teacher_id = ANY($2) AND is_deleted = false",
                data.student_id, list(data.primary_teacher_ids),
            )
            existing_ids = {str(r["primary_teacher_id"]) for r in existing}
            new_ids = [tid for tid in data.primary_teacher_ids if tid not in existing_ids]

            # 單筆：嚴格報錯
            if len(data.primary_teacher_ids) == 1:
                if not new_ids:
                    raise HTTPException(status_code=400, detail="此學生已指定該教師，請編輯現有設定")
                tid = new_ids[0]
                insert_data = {
                    "student_id": data.student_id,
                    "course_id": None,
                    "min_teacher_level": None,
                    "primary_teacher_id": tid,
                }
                if employee_id:
                    insert_data["created_by"] = employee_id
                result = await supabase_service.table_insert(
                    table="student_teacher_preferences", data=insert_data,
                )
                if not result:
                    raise HTTPException(status_code=500, detail="建立偏好失敗")
                enriched = await enrich_preference(result)
                return DataResponse(
                    message="偏好建立成功",
                    data=StudentTeacherPreferenceResponse(**enriched)
                )

            # 多筆：批次建立，跳過重複
            if not new_ids:
                raise HTTPException(status_code=400, detail="所有選擇的教師已存在於偏好中")

            created = []
            for tid in new_ids:
                insert_data = {
                    "student_id": data.student_id,
                    "course_id": None,
                    "min_teacher_level": None,
                    "primary_teacher_id": tid,
                }
                if employee_id:
                    insert_data["created_by"] = employee_id
                result = await supabase_service.table_insert(
                    table="student_teacher_preferences", data=insert_data,
                )
                if result:
                    created.append(result)

            skipped = len(data.primary_teacher_ids) - len(new_ids)
            msg = f"成功新增 {len(created)} 筆教師偏好"
            if skipped:
                msg += f"（跳過 {skipped} 筆已存在）"
            return {"success": True, "message": msg, "data": created}

        # ── 等級模式 ──
        if not data.min_teacher_level:
            raise HTTPException(status_code=400, detail="等級模式必須提供最高教師等級 (min_teacher_level)")

        if data.course_id:
            course = await supabase_service.table_select(
                table="courses", select="id",
                filters={"id": data.course_id, "is_deleted": "eq.false"},
            )
            if not course:
                raise HTTPException(status_code=400, detail="課程不存在")

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
            table="student_teacher_preferences", select="id", filters=dup_filters,
        )
        if existing:
            scope = "全域" if not data.course_id else "該課程"
            raise HTTPException(status_code=400, detail=f"此學生已有{scope}等級偏好設定，請編輯現有設定")

        insert_data = {
            "student_id": data.student_id,
            "course_id": data.course_id,
            "min_teacher_level": data.min_teacher_level,
            "primary_teacher_id": None,
        }
        if employee_id:
            insert_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="student_teacher_preferences", data=insert_data,
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
    current_user: CurrentUser = Depends(require_page_permission("students.edit"))
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
    current_user: CurrentUser = Depends(require_page_permission("students.edit"))
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
