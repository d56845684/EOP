from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_page_permission, get_user_employee_id
from app.schemas.student import (
    StudentCreate, StudentUpdate, StudentResponse, StudentListResponse,
    ConvertToFormalRequest, ConvertToFormalResponse, ConvertToFormalContractInfo,
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime, date
import math
import uuid

router = APIRouter(prefix="/students", tags=["學生管理"])

STUDENT_SELECT = "id,student_no,name,email,phone,address,birth_date,student_type,is_active,email_verified_at,created_at,updated_at"


@router.get("", response_model=StudentListResponse)
async def list_students(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜尋（編號/姓名/email）"),
    is_active: Optional[bool] = Query(None),
    student_type: Optional[str] = Query(None, description="學生類型 (formal/trial)"),
    current_user: CurrentUser = Depends(require_page_permission("students.list"))
):
    """取得學生列表"""
    try:
        filters = {"is_deleted": "eq.false"}
        if is_active is not None:
            filters["is_active"] = f"eq.{str(is_active).lower()}"
        if student_type:
            filters["student_type"] = f"eq.{student_type}"

        all_students = await supabase_service.table_select(
            table="students", select="id", filters=filters
        )
        total = len(all_students)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        students = await supabase_service.table_select_with_pagination(
            table="students", select=STUDENT_SELECT, filters=filters,
            order_by="created_at.desc", limit=per_page, offset=offset
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
    current_user: CurrentUser = Depends(require_page_permission("students.list"))
):
    """取得單一學生"""
    try:
        result = await supabase_service.table_select(
            table="students", select=STUDENT_SELECT,
            filters={"id": student_id, "is_deleted": "eq.false"}
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
    current_user: CurrentUser = Depends(require_page_permission("students.create"))
):
    """建立學生（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="students", select="id",
            filters={"student_no": data.student_no, "is_deleted": "eq.false"}
        )
        if existing:
            raise HTTPException(status_code=400, detail="學生編號已存在")

        existing_email = await supabase_service.table_select(
            table="students", select="id",
            filters={"email": data.email, "is_deleted": "eq.false"}
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
            table="students", data=student_data
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
    current_user: CurrentUser = Depends(require_page_permission("students.edit"))
):
    """更新學生（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="students", select="id,student_no,email",
            filters={"id": student_id, "is_deleted": "eq.false"}
        )
        if not existing:
            raise HTTPException(status_code=404, detail="學生不存在")

        if data.email and data.email != existing[0]["email"]:
            dup = await supabase_service.table_select(
                table="students", select="id",
                filters={"email": data.email, "is_deleted": "eq.false"}
            )
            if dup:
                raise HTTPException(status_code=400, detail="Email 已存在")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if "birth_date" in update_data and update_data["birth_date"]:
            update_data["birth_date"] = update_data["birth_date"].isoformat()

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="students", data=update_data, filters={"id": student_id}
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
    current_user: CurrentUser = Depends(require_page_permission("students.delete"))
):
    """刪除學生（軟刪除，僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="students", select="id",
            filters={"id": student_id, "is_deleted": "eq.false"}
        )
        if not existing:
            raise HTTPException(status_code=404, detail="學生不存在")

        result = await supabase_service.table_update(
            table="students",
            data={"is_deleted": True, "deleted_at": datetime.utcnow().isoformat()},
            filters={"id": student_id}
        )
        if not result:
            raise HTTPException(status_code=500, detail="刪除學生失敗")

        return BaseResponse(message="學生刪除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除學生失敗: {str(e)}")


@router.post("/{student_id}/convert-to-formal", response_model=ConvertToFormalResponse)
async def convert_to_formal(
    student_id: str,
    data: ConvertToFormalRequest,
    current_user: CurrentUser = Depends(require_page_permission("students.edit"))
):
    """試上學生轉正式學生（僅限員工）

    1. 驗證學生為 trial 類型
    2. 更新 student_type → formal
    3. 建立 student_contracts（status=active）
    4. 若提供 teacher_id，記錄轉正獎金
    """
    try:
        # 1. 驗證學生存在且為 trial
        students = await supabase_service.table_select(
            table="students", select=STUDENT_SELECT,
            filters={"id": student_id, "is_deleted": "eq.false"},
        )
        if not students:
            raise HTTPException(status_code=404, detail="學生不存在")

        student = students[0]
        if student.get("student_type") != "trial":
            raise HTTPException(status_code=400, detail="此學生非試上學生，無法執行轉正")

        # 1.5 驗證 booking_id 為 trial、已完成、且未轉正
        if data.booking_id:
            booking_rows = await supabase_service.pool.fetch(
                """
                SELECT id, booking_type, booking_status, is_trial_to_formal
                FROM bookings_view
                WHERE id = $1 AND is_deleted = FALSE
                """,
                uuid.UUID(data.booking_id),
            )
            if not booking_rows:
                raise HTTPException(status_code=404, detail="預約不存在")
            bk = booking_rows[0]
            if bk["booking_type"] != "trial":
                raise HTTPException(status_code=400, detail="只能選擇試上類型的預約")
            if bk["booking_status"] != "completed":
                raise HTTPException(status_code=400, detail="預約狀態必須為已完成")
            if bk["is_trial_to_formal"]:
                raise HTTPException(status_code=400, detail="此預約已被標記為轉正")

        # 2. 更新 student_type → formal
        updated_student = await supabase_service.table_update(
            table="students",
            data={"student_type": "formal"},
            filters={"id": student_id},
        )
        if not updated_student:
            raise HTTPException(status_code=500, detail="更新學生類型失敗")

        # 3. 建立 student_contracts
        employee_id = await get_user_employee_id(current_user.user_id)
        contract_data = {
            "contract_no": data.contract_no,
            "student_id": student_id,
            "contract_status": "active",
            "start_date": data.start_date.isoformat(),
            "end_date": data.end_date.isoformat(),
            "total_lessons": data.total_lessons,
            "total_amount": data.total_amount,
            "remaining_lessons": data.total_lessons,
            "total_leave_allowed": data.total_lessons * 2,
            "notes": data.notes,
        }
        if employee_id:
            contract_data["created_by"] = employee_id

        contract = await supabase_service.table_insert(
            table="student_contracts", data=contract_data
        )
        if not contract:
            raise HTTPException(status_code=500, detail="建立合約失敗")

        # 4. 若提供 teacher_id，查 trial_to_formal_bonus 並記錄
        bonus_recorded = False
        bonus_amount = None
        if data.teacher_id:
            try:
                tc_list = await supabase_service.table_select(
                    table="teacher_contracts",
                    select="id,trial_to_formal_bonus",
                    filters={
                        "teacher_id": data.teacher_id,
                        "contract_status": "eq.active",
                        "is_deleted": "eq.false",
                    },
                )
                if tc_list:
                    bonus = tc_list[0].get("trial_to_formal_bonus", 0) or 0
                    bonus_amount = float(bonus)
                    bonus_recorded = True
                    # 寫入 teacher_bonus_records
                    try:
                        bonus_data = {
                            "teacher_id": data.teacher_id,
                            "bonus_type": "trial_to_formal",
                            "amount": bonus_amount,
                            "bonus_date": date.today().isoformat(),
                            "description": f"學生 {student.get('name', '')} 試上轉正獎金",
                            "related_student_id": student_id,
                        }
                        if data.booking_id:
                            bonus_data["related_booking_id"] = data.booking_id
                        if employee_id:
                            bonus_data["created_by"] = employee_id
                        await supabase_service.table_insert(
                            table="teacher_bonus_records", data=bonus_data
                        )
                    except Exception:
                        pass  # 獎金寫入失敗不影響轉正流程
            except Exception:
                pass  # 獎金查詢失敗不影響轉正

        return ConvertToFormalResponse(
            student=StudentResponse(**updated_student),
            contract=ConvertToFormalContractInfo(**contract),
            bonus_recorded=bonus_recorded,
            bonus_amount=bonus_amount,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"試上轉正失敗: {str(e)}")
