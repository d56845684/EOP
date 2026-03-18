from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_page_permission, get_user_employee_id
from app.schemas.leave_record import (
    LeaveRecordCreate, LeaveRecordReject, LeaveRecordResponse, LeaveRecordListResponse
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime, date, timedelta
import math
import logging

router = APIRouter(prefix="/leave-records", tags=["請假管理"])
logger = logging.getLogger(__name__)


async def generate_leave_no() -> str:
    """生成請假編號: LV{YYYYMMDD}{序號}"""
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"LV{today}"

    result = await supabase_service.table_select(
        table="leave_records",
        select="leave_no",
        filters={"leave_no": f"like.{prefix}%"},
    )

    if not result:
        return f"{prefix}001"

    max_seq = 0
    for item in result:
        leave_no = item.get("leave_no", "")
        if leave_no.startswith(prefix):
            try:
                seq = int(leave_no[len(prefix):])
                max_seq = max(max_seq, seq)
            except ValueError:
                pass

    return f"{prefix}{str(max_seq + 1).zfill(3)}"


async def enrich_leave_record(record: dict) -> dict:
    """為請假紀錄添加關聯名稱"""
    # 發起者名稱
    if record.get("initiator_type") == "student" and record.get("initiator_student_id"):
        student = await supabase_service.table_select(
            table="students", select="name",
            filters={"id": record["initiator_student_id"]},
        )
        record["initiator_name"] = student[0]["name"] if student else None
    elif record.get("initiator_type") == "teacher" and record.get("initiator_teacher_id"):
        teacher = await supabase_service.table_select(
            table="teachers", select="name",
            filters={"id": record["initiator_teacher_id"]},
        )
        record["initiator_name"] = teacher[0]["name"] if teacher else None
    else:
        record["initiator_name"] = None

    # 預約編號
    if record.get("booking_id"):
        booking = await supabase_service.table_select(
            table="bookings", select="booking_no",
            filters={"id": record["booking_id"]},
        )
        record["booking_no"] = booking[0]["booking_no"] if booking else None
    else:
        record["booking_no"] = None

    # 審核者名稱
    if record.get("approver_id"):
        emp = await supabase_service.table_select(
            table="employees", select="name",
            filters={"id": record["approver_id"]},
        )
        record["approver_name"] = emp[0]["name"] if emp else None
    else:
        record["approver_name"] = None

    return record


@router.post("", response_model=DataResponse[LeaveRecordResponse])
async def create_leave_record(
    data: LeaveRecordCreate,
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """建立請假申請（學生/教師/員工皆可）"""
    try:
        # 驗證預約存在且為 confirmed
        booking = await supabase_service.table_select(
            table="bookings",
            select="id,booking_status,student_id,teacher_id,booking_date,start_time,end_time,student_contract_id",
            filters={"id": data.booking_id, "is_deleted": "eq.false"},
        )
        if not booking:
            raise HTTPException(status_code=404, detail="預約不存在")
        if booking[0].get("booking_status") != "confirmed":
            raise HTTPException(status_code=400, detail="只有已確認的預約可以請假")

        # 檢查是否已有 pending 的請假申請
        existing_leave = await supabase_service.table_select(
            table="leave_records",
            select="id",
            filters={
                "booking_id": f"eq.{data.booking_id}",
                "leave_status": "eq.pending",
                "is_deleted": "eq.false",
            },
        )
        if existing_leave:
            raise HTTPException(status_code=400, detail="此預約已有待審核的請假申請")

        # === 時間判定：正常 / 緊急 / 禁止 ===
        booking_date_str = booking[0].get("booking_date")  # "2026-03-20" or date obj
        booking_start_str = booking[0].get("start_time")    # "14:00:00" or time obj
        if isinstance(booking_date_str, date):
            booking_date_str = booking_date_str.isoformat()
        if hasattr(booking_start_str, 'isoformat'):
            booking_start_str = booking_start_str.isoformat()
        class_start_dt = datetime.strptime(f"{booking_date_str} {booking_start_str}", "%Y-%m-%d %H:%M:%S")
        now = datetime.utcnow() + timedelta(hours=8)  # UTC+8 台灣時間

        hours_before = (class_start_dt - now).total_seconds() / 3600

        if hours_before < 0.5:
            raise HTTPException(status_code=400, detail="課程開始前 30 分鐘內無法請假")

        if hours_before >= 24:
            leave_type = "normal"
            deduct_lesson = False
            emergency_quota = None
            used_emergency_count = None
        else:
            leave_type = "emergency"
            # 查合約額度
            student_id_for_quota = booking[0].get("student_id")
            contract_for_quota = await supabase_service.table_select(
                table="student_contracts",
                select="id,total_lessons,used_emergency_leave_count",
                filters={
                    "student_id": f"eq.{student_id_for_quota}",
                    "is_deleted": "eq.false",
                    "contract_status": "eq.active",
                },
            )
            if contract_for_quota:
                total_lessons = contract_for_quota[0].get("total_lessons", 0)
                emergency_quota = math.ceil(total_lessons * 0.2) if total_lessons else 0
                used_emergency_count = contract_for_quota[0].get("used_emergency_leave_count", 0)
                if used_emergency_count >= emergency_quota:
                    raise HTTPException(
                        status_code=400,
                        detail=f"緊急請假額度已用完（{used_emergency_count}/{emergency_quota}），無法請假",
                    )
            else:
                raise HTTPException(status_code=400, detail="查無有效合約，無法申請緊急請假")
            deduct_lesson = False

        # 判斷發起者類型
        if current_user.is_student():
            if booking[0].get("student_id") != current_user.student_id:
                raise HTTPException(status_code=403, detail="學生只能為自己的預約請假")
            initiator_type = "student"
            initiator_student_id = current_user.student_id
            initiator_teacher_id = None
        elif current_user.is_teacher():
            if booking[0].get("teacher_id") != current_user.teacher_id:
                raise HTTPException(status_code=403, detail="教師只能為自己的預約請假")
            initiator_type = "teacher"
            initiator_student_id = None
            initiator_teacher_id = current_user.teacher_id
        elif current_user.is_staff():
            # 員工代為申請，預設以學生身份
            initiator_type = "student"
            initiator_student_id = booking[0].get("student_id")
            initiator_teacher_id = None
        else:
            raise HTTPException(status_code=403, detail="無權建立請假申請")

        leave_no = await generate_leave_no()
        employee_id = await get_user_employee_id(current_user.user_id)

        leave_data = {
            "leave_no": leave_no,
            "initiator_type": initiator_type,
            "initiator_student_id": initiator_student_id,
            "initiator_teacher_id": initiator_teacher_id,
            "booking_id": data.booking_id,
            "leave_date": booking[0].get("booking_date"),
            "start_time": booking[0].get("start_time"),
            "end_time": booking[0].get("end_time"),
            "reason": data.reason,
            "leave_status": "pending",
            "leave_type": leave_type,
            "deduct_lesson": deduct_lesson,
        }
        if employee_id:
            leave_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="leave_records", data=leave_data,
        )

        if not result:
            raise HTTPException(status_code=500, detail="建立請假申請失敗")

        enriched = await enrich_leave_record(result)
        # 附帶額度資訊
        enriched["emergency_quota"] = emergency_quota
        enriched["used_emergency_count"] = used_emergency_count
        return DataResponse(message="請假申請已送出", data=LeaveRecordResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立請假申請失敗: {str(e)}")


@router.get("", response_model=LeaveRecordListResponse)
async def list_leave_records(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    leave_status: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得請假紀錄列表（依角色過濾）"""
    try:
        filters = {"is_deleted": "eq.false"}

        if leave_status:
            filters["leave_status"] = f"eq.{leave_status}"

        # 角色過濾
        if current_user.is_student():
            filters["initiator_student_id"] = f"eq.{current_user.student_id}"
        elif current_user.is_teacher():
            filters["initiator_teacher_id"] = f"eq.{current_user.teacher_id}"

        all_records = await supabase_service.table_select(
            table="leave_records", select="id", filters=filters,
        )
        total = len(all_records)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        records = await supabase_service.table_select_with_pagination(
            table="leave_records",
            select="id,leave_no,initiator_type,initiator_student_id,initiator_teacher_id,booking_id,leave_date,start_time,end_time,reason,leave_status,leave_type,deduct_lesson,approver_id,approved_at,rejection_reason,created_at,updated_at",
            filters=filters,
            order_by="created_at.desc",
            limit=per_page,
            offset=offset,
        )

        enriched = []
        for record in records:
            enriched.append(await enrich_leave_record(record))

        return LeaveRecordListResponse(
            data=[LeaveRecordResponse(**r) for r in enriched],
            total=total, page=page, per_page=per_page, total_pages=total_pages,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得請假紀錄失敗: {str(e)}")


@router.get("/{leave_id}", response_model=DataResponse[LeaveRecordResponse])
async def get_leave_record(
    leave_id: str,
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得單筆請假紀錄"""
    try:
        result = await supabase_service.table_select(
            table="leave_records",
            select="id,leave_no,initiator_type,initiator_student_id,initiator_teacher_id,booking_id,leave_date,start_time,end_time,reason,leave_status,leave_type,deduct_lesson,approver_id,approved_at,rejection_reason,created_at,updated_at",
            filters={"id": leave_id, "is_deleted": "eq.false"},
        )
        if not result:
            raise HTTPException(status_code=404, detail="請假紀錄不存在")

        # 權限檢查
        record = result[0]
        if current_user.is_student():
            if record.get("initiator_student_id") != current_user.student_id:
                raise HTTPException(status_code=403, detail="無權查看此請假紀錄")
        elif current_user.is_teacher():
            if record.get("initiator_teacher_id") != current_user.teacher_id:
                raise HTTPException(status_code=403, detail="無權查看此請假紀錄")

        enriched = await enrich_leave_record(record)
        return DataResponse(data=LeaveRecordResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得請假紀錄失敗: {str(e)}")


@router.post("/{leave_id}/approve", response_model=DataResponse[LeaveRecordResponse])
async def approve_leave_record(
    leave_id: str,
    current_user: CurrentUser = Depends(require_page_permission("bookings.edit"))
):
    """核准請假（僅限員工）— 觸發取消預約 + 寫入合約請假紀錄"""
    try:
        if not current_user.is_staff():
            raise HTTPException(status_code=403, detail="僅限員工核准請假")

        # 取得請假紀錄
        record = await supabase_service.table_select(
            table="leave_records",
            select="id,leave_status,booking_id,leave_date,reason,leave_type,deduct_lesson",
            filters={"id": leave_id, "is_deleted": "eq.false"},
        )
        if not record:
            raise HTTPException(status_code=404, detail="請假紀錄不存在")
        if record[0].get("leave_status") != "pending":
            raise HTTPException(status_code=400, detail="只有待審核的請假可以核准")

        booking_id = record[0].get("booking_id")

        # 取得預約資料
        booking = await supabase_service.table_select(
            table="bookings",
            select="id,booking_status,student_contract_id,teacher_slot_id,lessons_used,substitute_detail_id",
            filters={"id": booking_id, "is_deleted": "eq.false"},
        )
        if not booking:
            raise HTTPException(status_code=400, detail="關聯的預約不存在")

        has_substitute = booking[0].get("substitute_detail_id") is not None
        employee_id = await get_user_employee_id(current_user.user_id)

        # 1. 更新 leave_records 狀態
        await supabase_service.table_update(
            table="leave_records",
            data={
                "leave_status": "approved",
                "approver_id": employee_id,
                "approved_at": datetime.utcnow().isoformat(),
            },
            filters={"id": leave_id},
        )

        if has_substitute:
            # 已有代課 → 預約維持 confirmed，不取消
            pass
        else:
            # 無代課 → 取消預約
            # 2. 取消預約
            await supabase_service.table_update(
                table="bookings",
                data={"booking_status": "cancelled"},
                filters={"id": booking_id},
            )

            # 3. 觸發取消副作用（堂數歸還 + 時段釋放 + Zoom 取消）
            from app.api.v1.bookings import cancel_booking_side_effects
            await cancel_booking_side_effects(booking[0])

            # 4. 寫入 student_contract_leave_records
            student_contract_id = booking[0].get("student_contract_id")
            if student_contract_id:
                await supabase_service.table_insert(
                    table="student_contract_leave_records",
                    data={
                        "student_contract_id": student_contract_id,
                        "leave_date": record[0].get("leave_date"),
                        "reason": record[0].get("reason"),
                        "created_by": employee_id,
                    },
                )

                # 5. used_leave_count + 1
                contract = await supabase_service.table_select(
                    table="student_contracts",
                    select="used_leave_count,used_emergency_leave_count,remaining_lessons",
                    filters={"id": student_contract_id},
                )
                if contract:
                    current_count = contract[0].get("used_leave_count", 0) or 0
                    update_data = {"used_leave_count": current_count + 1}

                    # 6. 緊急請假：更新 used_emergency_leave_count
                    rec_leave_type = record[0].get("leave_type", "normal")

                    if rec_leave_type == "emergency":
                        current_emergency = contract[0].get("used_emergency_leave_count", 0) or 0
                        update_data["used_emergency_leave_count"] = current_emergency + 1

                    await supabase_service.table_update(
                        table="student_contracts",
                        data=update_data,
                        filters={"id": student_contract_id},
                    )

        # 重新取得更新後的紀錄
        updated = await supabase_service.table_select(
            table="leave_records",
            select="id,leave_no,initiator_type,initiator_student_id,initiator_teacher_id,booking_id,leave_date,start_time,end_time,reason,leave_status,leave_type,deduct_lesson,approver_id,approved_at,rejection_reason,created_at,updated_at",
            filters={"id": leave_id},
        )
        enriched = await enrich_leave_record(updated[0])
        return DataResponse(message="請假已核准", data=LeaveRecordResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"核准請假失敗: {str(e)}")


@router.post("/{leave_id}/reject", response_model=DataResponse[LeaveRecordResponse])
async def reject_leave_record(
    leave_id: str,
    data: LeaveRecordReject,
    current_user: CurrentUser = Depends(require_page_permission("bookings.edit"))
):
    """駁回請假（僅限員工）"""
    try:
        if not current_user.is_staff():
            raise HTTPException(status_code=403, detail="僅限員工駁回請假")

        record = await supabase_service.table_select(
            table="leave_records",
            select="id,leave_status",
            filters={"id": leave_id, "is_deleted": "eq.false"},
        )
        if not record:
            raise HTTPException(status_code=404, detail="請假紀錄不存在")
        if record[0].get("leave_status") != "pending":
            raise HTTPException(status_code=400, detail="只有待審核的請假可以駁回")

        employee_id = await get_user_employee_id(current_user.user_id)

        await supabase_service.table_update(
            table="leave_records",
            data={
                "leave_status": "rejected",
                "rejection_reason": data.rejection_reason,
                "approver_id": employee_id,
                "approved_at": datetime.utcnow().isoformat(),
            },
            filters={"id": leave_id},
        )

        updated = await supabase_service.table_select(
            table="leave_records",
            select="id,leave_no,initiator_type,initiator_student_id,initiator_teacher_id,booking_id,leave_date,start_time,end_time,reason,leave_status,leave_type,deduct_lesson,approver_id,approved_at,rejection_reason,created_at,updated_at",
            filters={"id": leave_id},
        )
        enriched = await enrich_leave_record(updated[0])
        return DataResponse(message="請假已駁回", data=LeaveRecordResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"駁回請假失敗: {str(e)}")


@router.post("/{leave_id}/cancel", response_model=DataResponse[LeaveRecordResponse])
async def cancel_leave_record(
    leave_id: str,
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """撤回請假申請（發起者或員工可操作）"""
    try:
        record = await supabase_service.table_select(
            table="leave_records",
            select="id,leave_status,initiator_type,initiator_student_id,initiator_teacher_id",
            filters={"id": leave_id, "is_deleted": "eq.false"},
        )
        if not record:
            raise HTTPException(status_code=404, detail="請假紀錄不存在")
        if record[0].get("leave_status") != "pending":
            raise HTTPException(status_code=400, detail="只有待審核的請假可以撤回")

        # 權限檢查：發起者本人或員工
        if current_user.is_student():
            if record[0].get("initiator_student_id") != current_user.student_id:
                raise HTTPException(status_code=403, detail="只有發起者可以撤回請假")
        elif current_user.is_teacher():
            if record[0].get("initiator_teacher_id") != current_user.teacher_id:
                raise HTTPException(status_code=403, detail="只有發起者可以撤回請假")
        elif not current_user.is_staff():
            raise HTTPException(status_code=403, detail="無權撤回請假")

        await supabase_service.table_update(
            table="leave_records",
            data={"leave_status": "cancelled"},
            filters={"id": leave_id},
        )

        updated = await supabase_service.table_select(
            table="leave_records",
            select="id,leave_no,initiator_type,initiator_student_id,initiator_teacher_id,booking_id,leave_date,start_time,end_time,reason,leave_status,leave_type,deduct_lesson,approver_id,approved_at,rejection_reason,created_at,updated_at",
            filters={"id": leave_id},
        )
        enriched = await enrich_leave_record(updated[0])
        return DataResponse(message="請假已撤回", data=LeaveRecordResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"撤回請假失敗: {str(e)}")
