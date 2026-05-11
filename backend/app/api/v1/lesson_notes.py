from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime
import asyncio
import logging
import uuid

from app.services.supabase_service import supabase_service
from app.services.line_message_service import line_message_service
from app.config import ChannelType
from app.core.dependencies import get_current_user, CurrentUser
from app.schemas.lesson_note import LessonNoteUploadRequest, LessonNoteResponse
from app.schemas.response import DataResponse
from app.api.v1.bookings import apply_booking_completed_side_effects

router = APIRouter(prefix="/bookings/{booking_id}/lesson-note", tags=["課後筆記"])
logger = logging.getLogger(__name__)


async def _fetch_booking(booking_id: str) -> dict:
    rows = await supabase_service.table_select(
        table="bookings",
        select="id,booking_no,student_id,teacher_id,booking_status,booking_type,booking_date,start_time,teacher_contract_id,is_deleted",
        filters={"id": booking_id, "is_deleted": "eq.false"},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="預約不存在")
    return rows[0]


async def _fetch_lesson_note(booking_id: str) -> Optional[dict]:
    rows = await supabase_service.table_select(
        table="lesson_notes",
        select="*",
        filters={"booking_id": booking_id},
    )
    return rows[0] if rows else None


async def _resolve_line_user_id(role: ChannelType, role_entity_id: str) -> Optional[str]:
    """從 entity (student/teacher) 找對應 channel 的 line_user_id。"""
    entity_col = {"student": "student_id", "teacher": "teacher_id", "employee": "employee_id"}[role]
    sql = f"""
        SELECT lub.line_user_id
        FROM line_user_bindings lub
        JOIN user_profiles up ON up.id = lub.user_id
        WHERE up.{entity_col} = $1
          AND lub.channel_type = $2
          AND lub.binding_status = 'active'
        LIMIT 1
    """
    try:
        row = await supabase_service.pool.fetchrow(sql, role_entity_id, role)
        return row["line_user_id"] if row else None
    except Exception as e:
        logger.warning(f"_resolve_line_user_id 失敗: {e}")
        return None


async def _notify_student_note_uploaded(booking: dict, google_doc_url: str) -> None:
    """LINE 推學生：老師已上傳筆記。失敗只 log。"""
    try:
        student_id = booking.get("student_id")
        if not student_id:
            return
        line_user_id = await _resolve_line_user_id("student", student_id)
        if not line_user_id:
            logger.info(f"booking={booking.get('id')}：學生未綁定 LINE，略過通知")
            return
        booking_no = booking.get("booking_no") or booking.get("id")
        text = (
            f"📝 老師已上傳本堂課後筆記\n"
            f"預約編號：{booking_no}\n"
            f"筆記連結：{google_doc_url}\n"
            f"請點選連結查看，確認無誤後在系統內按「確認」"
        )
        await line_message_service.send_text_message(line_user_id, text, "student")
    except Exception as e:
        logger.warning(f"通知學生筆記上傳失敗: {e}")


async def _notify_teacher_note_confirmed(booking: dict, confirmed_by_role: str) -> None:
    """LINE 推老師：筆記已被確認。失敗只 log。"""
    try:
        teacher_id = booking.get("teacher_id")
        if not teacher_id:
            return
        line_user_id = await _resolve_line_user_id("teacher", teacher_id)
        if not line_user_id:
            logger.info(f"booking={booking.get('id')}：老師未綁定 LINE，略過通知")
            return
        booking_no = booking.get("booking_no") or booking.get("id")
        who = "學生" if confirmed_by_role == "student" else "管理員"
        text = (
            f"✅ {who}已確認本堂課後筆記\n"
            f"預約編號：{booking_no}\n"
            f"預約狀態已轉為完成"
        )
        await line_message_service.send_text_message(line_user_id, text, "teacher")
    except Exception as e:
        logger.warning(f"通知老師筆記確認失敗: {e}")


def _to_response(row: dict) -> LessonNoteResponse:
    return LessonNoteResponse(
        id=str(row["id"]),
        booking_id=str(row["booking_id"]),
        google_doc_url=row["google_doc_url"],
        status=row["status"],
        uploaded_by=str(row["uploaded_by"]),
        uploaded_at=row["uploaded_at"],
        confirmed_by=str(row["confirmed_by"]) if row.get("confirmed_by") else None,
        confirmed_by_role=row.get("confirmed_by_role"),
        confirmed_at=row.get("confirmed_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("", response_model=DataResponse[LessonNoteResponse])
async def upload_lesson_note(
    booking_id: str,
    data: LessonNoteUploadRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """老師上傳課後筆記（Google Doc URL）。"""
    booking = await _fetch_booking(booking_id)

    # 權限：只有該 booking 的老師
    if not current_user.teacher_id or current_user.teacher_id != booking["teacher_id"]:
        raise HTTPException(status_code=403, detail="只有該預約的老師可以上傳課後筆記")

    # booking 必須是 confirmed
    if booking["booking_status"] != "confirmed":
        raise HTTPException(
            status_code=400,
            detail=f"預約狀態為 {booking['booking_status']}，無法上傳筆記（須為 confirmed）",
        )

    # 不允許重複上傳（MVP）
    if await _fetch_lesson_note(booking_id):
        raise HTTPException(status_code=409, detail="此預約已上傳過筆記")

    new_id = str(uuid.uuid4())
    await supabase_service.table_insert(
        table="lesson_notes",
        data={
            "id": new_id,
            "booking_id": booking_id,
            "google_doc_url": data.google_doc_url,
            "status": "pending_confirmation",
            "uploaded_by": current_user.user_id,
        },
    )

    # 非同步推 LINE 給學生
    asyncio.create_task(_notify_student_note_uploaded(booking, data.google_doc_url))

    note = await _fetch_lesson_note(booking_id)
    return DataResponse(message="課後筆記已上傳，等待確認", data=_to_response(note))


@router.put("", response_model=DataResponse[LessonNoteResponse])
async def update_lesson_note(
    booking_id: str,
    data: LessonNoteUploadRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """老師修改尚未被確認的筆記 URL。已確認後不可修改。"""
    booking = await _fetch_booking(booking_id)

    if not current_user.teacher_id or current_user.teacher_id != booking["teacher_id"]:
        raise HTTPException(status_code=403, detail="只有該預約的老師可以修改筆記")

    note = await _fetch_lesson_note(booking_id)
    if not note:
        raise HTTPException(status_code=404, detail="尚未上傳課後筆記，無法修改")
    if note["status"] == "confirmed":
        raise HTTPException(status_code=409, detail="筆記已被確認，無法修改")

    await supabase_service.table_update(
        table="lesson_notes",
        data={"google_doc_url": data.google_doc_url},
        filters={"id": note["id"]},
    )

    updated = await _fetch_lesson_note(booking_id)
    return DataResponse(message="筆記已更新", data=_to_response(updated))


@router.get("", response_model=DataResponse[Optional[LessonNoteResponse]])
async def get_lesson_note(
    booking_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """查詢課後筆記（老師/學生/員工皆可）。未上傳回 data=null。"""
    booking = await _fetch_booking(booking_id)

    is_authorized = (
        (current_user.teacher_id and current_user.teacher_id == booking["teacher_id"]) or
        (current_user.student_id and current_user.student_id == booking["student_id"]) or
        current_user.is_staff()
    )
    if not is_authorized:
        raise HTTPException(status_code=403, detail="無權限查看此筆記")

    note = await _fetch_lesson_note(booking_id)
    return DataResponse(data=_to_response(note) if note else None)


@router.post("/confirm", response_model=DataResponse[LessonNoteResponse])
async def confirm_lesson_note(
    booking_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """學生或員工/管理員確認筆記（先到先得）→ booking 轉 completed。"""
    booking = await _fetch_booking(booking_id)

    is_student_of_booking = (
        current_user.student_id and current_user.student_id == booking["student_id"]
    )
    is_employee = current_user.is_staff()
    if not (is_student_of_booking or is_employee):
        raise HTTPException(status_code=403, detail="只有該預約的學生或員工可以確認")

    # 只允許從 confirmed / completed 兩種狀態確認筆記
    # cancelled / pending 都不該被「確認筆記」這個動作復活或跳過正常流程
    if booking["booking_status"] not in ("confirmed", "completed"):
        raise HTTPException(
            status_code=400,
            detail=f"預約狀態為 {booking['booking_status']}，無法確認筆記",
        )

    note = await _fetch_lesson_note(booking_id)
    if not note:
        raise HTTPException(status_code=404, detail="尚未上傳課後筆記")
    if note["status"] == "confirmed":
        raise HTTPException(status_code=409, detail="筆記已被確認過")

    confirmed_by_role = "student" if is_student_of_booking else "employee"

    # lesson_note → confirmed
    await supabase_service.table_update(
        table="lesson_notes",
        data={
            "status": "confirmed",
            "confirmed_by": current_user.user_id,
            "confirmed_by_role": confirmed_by_role,
            "confirmed_at": datetime.utcnow().isoformat(),
        },
        filters={"id": note["id"]},
    )

    # booking → completed（共用 helper 觸發 Zoom 清理 + 試上獎金等副作用）
    if booking["booking_status"] != "completed":
        await supabase_service.table_update(
            table="bookings",
            data={"booking_status": "completed"},
            filters={"id": booking_id},
        )
        await apply_booking_completed_side_effects(booking, booking_id, current_user)

    # 非同步推 LINE 給老師
    asyncio.create_task(_notify_teacher_note_confirmed(booking, confirmed_by_role))

    updated = await _fetch_lesson_note(booking_id)
    return DataResponse(message="筆記已確認，預約狀態已更新為完成", data=_to_response(updated))
