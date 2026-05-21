from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_page_permission, get_user_employee_id
from app.core.error_codes import ErrorCode
from app.core.exceptions import (
    bad_request, forbidden, not_found, internal_error,
)
from app.schemas.leave_record import (
    LeaveRecordCreate, LeaveRecordReject, LeaveRecordResponse, LeaveRecordListResponse
)
from app.schemas.response import BaseResponse, DataResponse
from app.api.v1.student_contracts import compute_emergency_leave_quota
from typing import Optional
from datetime import datetime, date
import math
import uuid
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
    """為請假紀錄添加關聯名稱（單筆用，列表用 batch 版本）"""
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


async def list_leave_records_with_joins(
    filters: dict,
    per_page: int,
    offset: int,
) -> tuple[list[dict], int]:
    """使用 JOIN 一次查詢請假紀錄 + 關聯名稱 + 總筆數（消除 N+1）"""
    conditions = ["lr.is_deleted = false"]
    params: list = []
    idx = 1

    if filters.get("leave_status"):
        conditions.append(f"lr.leave_status = ${idx}")
        params.append(filters["leave_status"].replace("eq.", ""))
        idx += 1
    if filters.get("initiator_student_id"):
        conditions.append(f"lr.initiator_student_id = ${idx}::uuid")
        params.append(filters["initiator_student_id"].replace("eq.", ""))
        idx += 1
    if filters.get("initiator_teacher_id"):
        conditions.append(f"lr.initiator_teacher_id = ${idx}::uuid")
        params.append(filters["initiator_teacher_id"].replace("eq.", ""))
        idx += 1

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            lr.id, lr.leave_no, lr.initiator_type,
            lr.initiator_student_id, lr.initiator_teacher_id,
            lr.booking_id, lr.leave_date, lr.start_time, lr.end_time,
            lr.reason, lr.leave_status, lr.leave_type, lr.deduct_lesson,
            lr.approver_id, lr.approved_at, lr.rejection_reason,
            lr.created_at, lr.updated_at,
            COALESCE(s.name, t.name) AS initiator_name,
            b.booking_no,
            e.name AS approver_name,
            COUNT(*) OVER() AS _total
        FROM leave_records lr
        LEFT JOIN students s ON lr.initiator_student_id = s.id AND lr.initiator_type = 'student'
        LEFT JOIN teachers t ON lr.initiator_teacher_id = t.id AND lr.initiator_type = 'teacher'
        LEFT JOIN bookings b ON lr.booking_id = b.id
        LEFT JOIN employees e ON lr.approver_id = e.id
        WHERE {where_clause}
        ORDER BY lr.created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    params.extend([per_page, offset])

    rows = await supabase_service.pool.fetch(sql, *params)

    if not rows:
        return [], 0

    total = rows[0]["_total"]
    records = []
    for row in rows:
        record = dict(row)
        del record["_total"]
        # UUID / date 轉字串
        for key, val in record.items():
            if hasattr(val, 'hex'):  # UUID
                record[key] = str(val)
            elif hasattr(val, 'isoformat'):
                record[key] = val.isoformat()
        records.append(record)

    return records, total


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
            raise not_found("預約", ErrorCode.BOOKING_NOT_FOUND)
        if booking[0].get("booking_status") != "confirmed":
            raise bad_request("只有已確認的預約可以請假", ErrorCode.BOOKING_LEAVE_BOOKING_NOT_CONFIRMED)

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
            raise bad_request("此預約已有待審核的請假申請", ErrorCode.BOOKING_LEAVE_PENDING_ALREADY_EXISTS)

        # === 先決定 initiator_type（緊急請假豁免邏輯依賴它）===
        if current_user.is_student():
            if booking[0].get("student_id") != current_user.student_id:
                raise forbidden("學生只能為自己的預約請假", ErrorCode.BOOKING_LEAVE_FORBIDDEN_STUDENT_NOT_OWN)
            initiator_type = "student"
            initiator_student_id = current_user.student_id
            initiator_teacher_id = None
        elif current_user.is_teacher():
            if booking[0].get("teacher_id") != current_user.teacher_id:
                raise forbidden("教師只能為自己的預約請假", ErrorCode.BOOKING_LEAVE_FORBIDDEN_TEACHER_NOT_OWN)
            initiator_type = "teacher"
            initiator_student_id = None
            initiator_teacher_id = current_user.teacher_id
        elif current_user.is_staff():
            # 員工代申請：必須指定 initiator_type=student 或 teacher
            if data.initiator_type not in ("student", "teacher"):
                raise bad_request("員工代申請請假時須指定 initiator_type=student 或 teacher", ErrorCode.BOOKING_LEAVE_INITIATOR_TYPE_REQUIRED)
            initiator_type = data.initiator_type
            if initiator_type == "student":
                initiator_student_id = booking[0].get("student_id")
                initiator_teacher_id = None
            else:
                initiator_student_id = None
                initiator_teacher_id = booking[0].get("teacher_id")
        else:
            raise forbidden("無權建立請假申請", ErrorCode.BOOKING_LEAVE_FORBIDDEN_CREATE)

        # === 時間判定：正常 / 緊急 / 禁止 ===
        booking_date_str = booking[0].get("booking_date")  # "2026-03-20" or date obj
        booking_start_str = booking[0].get("start_time")    # "14:00:00" or time obj
        if isinstance(booking_date_str, date):
            booking_date_str = booking_date_str.isoformat()
        if hasattr(booking_start_str, 'isoformat'):
            booking_start_str = booking_start_str.isoformat()
        class_start_dt = datetime.strptime(f"{booking_date_str} {booking_start_str}", "%Y-%m-%d %H:%M:%S")
        now = datetime.now()  # container TZ=Asia/Taipei，naive Taipei

        hours_before = (class_start_dt - now).total_seconds() / 3600

        if hours_before < 0.5:
            raise bad_request("課程開始前 30 分鐘內無法請假", ErrorCode.BOOKING_LEAVE_TOO_LATE)

        if hours_before >= 24:
            leave_type = "normal"
            deduct_lesson = False
            emergency_quota = None
            used_emergency_count = None
        else:
            leave_type = "emergency"
            deduct_lesson = False
            # 緊急請假額度綁在學生合約上：
            # - 老師發起（含員工代老師申請）：不消耗學生額度，跳過合約檢查
            # - 學生發起 / 員工代學生申請：須檢查該預約對應的學生合約額度
            if initiator_type == "teacher":
                emergency_quota = None
                used_emergency_count = None
            else:
                # 優先用 booking 已綁定的 student_contract_id，與 contract_status 解耦——
                # 避免合約轉為 expired/terminated 後，既有預約的緊急請假被誤擋
                contract_id_for_quota = booking[0].get("student_contract_id")
                if contract_id_for_quota:
                    contract_for_quota = await supabase_service.table_select(
                        table="student_contracts",
                        select="id,total_lessons,used_emergency_leave_count",
                        filters={
                            "id": f"eq.{contract_id_for_quota}",
                            "is_deleted": "eq.false",
                        },
                    )
                else:
                    # fallback：舊資料 booking 未綁合約時，仍用 student_id 撈 active 合約
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
                    contract_id_resolved = contract_for_quota[0]["id"]
                    # 額度公式與 student_contracts enrich 共用 helper（含補償堂數）
                    quota_details = await supabase_service.table_select(
                        table="student_contract_details",
                        select="detail_type,amount",
                        filters={
                            "student_contract_id": f"eq.{contract_id_resolved}",
                            "is_deleted": "eq.false",
                        },
                    )
                    emergency_quota = compute_emergency_leave_quota(
                        contract_for_quota[0].get("total_lessons", 0), quota_details
                    )
                    used_emergency_count = contract_for_quota[0].get("used_emergency_leave_count", 0) or 0
                    # 把同合約底下「審核中」的緊急請假也算進額度——避免跨 booking
                    # 開多筆 pending 都通過 create 檢查、累積核准後超額。
                    # 老師發起的 pending 不消耗學生額度（與建立/核准對稱），故排除。
                    contract_id_uuid = (
                        uuid.UUID(contract_id_resolved)
                        if isinstance(contract_id_resolved, str)
                        else contract_id_resolved
                    )
                    pending_emergency_count = await supabase_service.pool.fetchval(
                        """
                        SELECT COUNT(*)
                        FROM leave_records lr
                        JOIN bookings b ON b.id = lr.booking_id
                        WHERE b.student_contract_id = $1
                          AND lr.leave_type = 'emergency'
                          AND lr.leave_status = 'pending'
                          AND lr.is_deleted = FALSE
                          AND lr.initiator_type != 'teacher'
                        """,
                        contract_id_uuid,
                    ) or 0
                    if used_emergency_count + pending_emergency_count >= emergency_quota:
                        raise bad_request((
                                f"緊急請假額度已用完（已核准 {used_emergency_count} 筆 + "
                                f"審核中 {pending_emergency_count} 筆 / 額度 {emergency_quota}），無法請假"
                            ), ErrorCode.BOOKING_LEAVE_EMERGENCY_QUOTA_EXCEEDED)
                else:
                    raise bad_request("此預約查無對應的學生合約，無法申請緊急請假", ErrorCode.BOOKING_LEAVE_NO_STUDENT_CONTRACT)

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
            raise internal_error("建立請假申請失敗", ErrorCode.BOOKING_LEAVE_CREATE_FAILED)

        enriched = await enrich_leave_record(result)
        # 附帶額度資訊
        enriched["emergency_quota"] = emergency_quota
        enriched["used_emergency_count"] = used_emergency_count
        return DataResponse(message="請假申請已送出", data=LeaveRecordResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"建立請假申請失敗: {str(e)}", ErrorCode.BOOKING_LEAVE_CREATE_FAILED)


@router.get("", response_model=LeaveRecordListResponse)
async def list_leave_records(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    leave_status: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得請假紀錄列表（依角色過濾）— 使用 JOIN 消除 N+1"""
    try:
        filters: dict = {}

        if leave_status:
            filters["leave_status"] = f"eq.{leave_status}"

        # 角色過濾
        if current_user.is_student():
            filters["initiator_student_id"] = f"eq.{current_user.student_id}"
        elif current_user.is_teacher():
            filters["initiator_teacher_id"] = f"eq.{current_user.teacher_id}"

        offset = (page - 1) * per_page
        records, total = await list_leave_records_with_joins(filters, per_page, offset)
        total_pages = math.ceil(total / per_page) if total > 0 else 1

        return LeaveRecordListResponse(
            data=[LeaveRecordResponse(**r) for r in records],
            total=total, page=page, per_page=per_page, total_pages=total_pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"取得請假紀錄失敗: {str(e)}", ErrorCode.BOOKING_LEAVE_LIST_FAILED)


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
            raise not_found("請假紀錄", ErrorCode.BOOKING_LEAVE_NOT_FOUND)

        # 權限檢查
        record = result[0]
        if current_user.is_student():
            if record.get("initiator_student_id") != current_user.student_id:
                raise forbidden("無權查看此請假紀錄", ErrorCode.BOOKING_LEAVE_FORBIDDEN_VIEW)
        elif current_user.is_teacher():
            if record.get("initiator_teacher_id") != current_user.teacher_id:
                raise forbidden("無權查看此請假紀錄", ErrorCode.BOOKING_LEAVE_FORBIDDEN_VIEW)

        enriched = await enrich_leave_record(record)
        return DataResponse(data=LeaveRecordResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"取得請假紀錄失敗: {str(e)}", ErrorCode.BOOKING_LEAVE_LIST_FAILED)


@router.post("/{leave_id}/approve", response_model=DataResponse[LeaveRecordResponse])
async def approve_leave_record(
    leave_id: str,
    current_user: CurrentUser = Depends(require_page_permission("bookings.edit"))
):
    """核准請假（僅限員工）— 觸發取消預約 + 寫入合約請假紀錄"""
    try:
        if not current_user.is_staff():
            raise forbidden("僅限員工核准請假", ErrorCode.BOOKING_LEAVE_FORBIDDEN_APPROVE)

        # 取得請假紀錄
        record = await supabase_service.table_select(
            table="leave_records",
            select="id,leave_status,booking_id,leave_date,reason,leave_type,deduct_lesson,initiator_type",
            filters={"id": leave_id, "is_deleted": "eq.false"},
        )
        if not record:
            raise not_found("請假紀錄", ErrorCode.BOOKING_LEAVE_NOT_FOUND)
        if record[0].get("leave_status") != "pending":
            raise bad_request("只有待審核的請假可以核准", ErrorCode.BOOKING_LEAVE_ONLY_PENDING_CAN_APPROVE)

        booking_id = record[0].get("booking_id")

        # 取得預約資料
        booking = await supabase_service.table_select(
            table="bookings",
            select="id,booking_status,student_contract_id,teacher_slot_id,lessons_used,substitute_detail_id",
            filters={"id": booking_id, "is_deleted": "eq.false"},
        )
        if not booking:
            raise bad_request("關聯的預約不存在", ErrorCode.BOOKING_LEAVE_RELATED_BOOKING_NOT_EXIST)

        has_substitute = booking[0].get("substitute_detail_id") is not None
        employee_id = await get_user_employee_id(current_user.user_id)

        # Fail-safe：核准緊急請假前再驗一次額度。
        # 建立檢查若被 race 繞過、或部署前已有 pending 累積，這裡兜底擋下。
        # 老師發起不消耗學生額度（與建立 / 寫入合約對稱），故排除。
        rec_leave_type_for_check = record[0].get("leave_type", "normal")
        rec_initiator_type_for_check = record[0].get("initiator_type")
        sc_id_for_check = booking[0].get("student_contract_id")
        if (
            rec_leave_type_for_check == "emergency"
            and rec_initiator_type_for_check != "teacher"
            and sc_id_for_check
        ):
            contract_check = await supabase_service.table_select(
                table="student_contracts",
                select="total_lessons,used_emergency_leave_count",
                filters={"id": sc_id_for_check, "is_deleted": "eq.false"},
            )
            if contract_check:
                quota_details = await supabase_service.table_select(
                    table="student_contract_details",
                    select="detail_type,amount",
                    filters={
                        "student_contract_id": f"eq.{sc_id_for_check}",
                        "is_deleted": "eq.false",
                    },
                )
                quota_check = compute_emergency_leave_quota(
                    contract_check[0].get("total_lessons", 0), quota_details
                )
                used_check = contract_check[0].get("used_emergency_leave_count", 0) or 0
                if used_check >= quota_check:
                    raise bad_request(f"緊急請假額度已用完（{used_check}/{quota_check}），無法核准", ErrorCode.BOOKING_LEAVE_EMERGENCY_QUOTA_EXCEEDED)

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

            # 4-6. 老師發起的請假不計入學生合約：不寫合約請假紀錄、
            # 不增 used_leave_count、不增 used_emergency_leave_count。
            # 堂數由 cancel_booking_side_effects 退還，學生不該被老師請假扣額度。
            rec_initiator_type = record[0].get("initiator_type")
            student_contract_id = booking[0].get("student_contract_id")
            if student_contract_id and rec_initiator_type != "teacher":
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
        raise internal_error(f"核准請假失敗: {str(e)}", ErrorCode.BOOKING_LEAVE_APPROVE_FAILED)


@router.post("/{leave_id}/reject", response_model=DataResponse[LeaveRecordResponse])
async def reject_leave_record(
    leave_id: str,
    data: LeaveRecordReject,
    current_user: CurrentUser = Depends(require_page_permission("bookings.edit"))
):
    """駁回請假（僅限員工）"""
    try:
        if not current_user.is_staff():
            raise forbidden("僅限員工駁回請假", ErrorCode.BOOKING_LEAVE_FORBIDDEN_REJECT)

        record = await supabase_service.table_select(
            table="leave_records",
            select="id,leave_status",
            filters={"id": leave_id, "is_deleted": "eq.false"},
        )
        if not record:
            raise not_found("請假紀錄", ErrorCode.BOOKING_LEAVE_NOT_FOUND)
        if record[0].get("leave_status") != "pending":
            raise bad_request("只有待審核的請假可以駁回", ErrorCode.BOOKING_LEAVE_ONLY_PENDING_CAN_REJECT)

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
        raise internal_error(f"駁回請假失敗: {str(e)}", ErrorCode.BOOKING_LEAVE_REJECT_FAILED)


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
            raise not_found("請假紀錄", ErrorCode.BOOKING_LEAVE_NOT_FOUND)
        if record[0].get("leave_status") != "pending":
            raise bad_request("只有待審核的請假可以撤回", ErrorCode.BOOKING_LEAVE_ONLY_PENDING_CAN_WITHDRAW)

        # 權限檢查：發起者本人或員工
        if current_user.is_student():
            if record[0].get("initiator_student_id") != current_user.student_id:
                raise forbidden("只有發起者可以撤回請假", ErrorCode.BOOKING_LEAVE_FORBIDDEN_NOT_INITIATOR)
        elif current_user.is_teacher():
            if record[0].get("initiator_teacher_id") != current_user.teacher_id:
                raise forbidden("只有發起者可以撤回請假", ErrorCode.BOOKING_LEAVE_FORBIDDEN_NOT_INITIATOR)
        elif not current_user.is_staff():
            raise forbidden("無權撤回請假", ErrorCode.BOOKING_LEAVE_FORBIDDEN_WITHDRAW)

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
        raise internal_error(f"撤回請假失敗: {str(e)}", ErrorCode.BOOKING_LEAVE_WITHDRAW_FAILED)
