from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_page_permission, get_user_employee_id
from app.schemas.booking import (
    BookingCreate, BookingUpdate, BookingResponse, BookingListResponse, BookingStatus,
    BookingBatchUpdateByIds, BookingBatchDeleteByIds, BookingBatchUpdate, BookingBatchDelete,
    BookingBatchCreate, TimeBlock, SlotAvailabilityResponse
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import date, datetime, time
import asyncio
import logging
import math
import uuid

router = APIRouter(prefix="/bookings", tags=["預約管理"])


def calculate_lessons_used(start_time: time, end_time: time, duration_minutes: int) -> int:
    """計算預約使用堂數 = 預約時長 / 課程單堂時長"""
    booking_minutes = (end_time.hour * 60 + end_time.minute) - (start_time.hour * 60 + start_time.minute)
    return max(1, booking_minutes // duration_minutes)


def calculate_regular_overtime_lessons(
    booking_start: time,
    booking_end: time,
    work_slots: list[tuple[time, time]],
    duration_minutes: int,
) -> tuple[int, int]:
    """依課程時長拆分正班 / 加班堂數

    以 duration_minutes 為一堂，從 booking_start 開始逐堂判斷：
    - 該堂完全落在任一 work_slot [start, end] 內 → 正班
    - 否則 → 加班

    work_slots: list of (start_time, end_time) tuples

    Returns: (regular_lessons, overtime_lessons)
    """
    # 將 work_slots 轉為分鐘區間
    slot_mins = []
    for ws, we in work_slots:
        slot_mins.append((ws.hour * 60 + ws.minute, we.hour * 60 + we.minute))

    bs_min = booking_start.hour * 60 + booking_start.minute
    be_min = booking_end.hour * 60 + booking_end.minute

    regular = 0
    overtime = 0
    cursor = bs_min
    while cursor + duration_minutes <= be_min:
        lesson_end = cursor + duration_minutes
        is_regular = any(
            cursor >= ws_min and lesson_end <= we_min
            for ws_min, we_min in slot_mins
        )
        if is_regular:
            regular += 1
        else:
            overtime += 1
        cursor += duration_minutes

    return regular, overtime


async def compute_overtime_pay(
    teacher_contract_id: str,
    booking_date: date,
    start_time: time,
    end_time: time,
    course_duration: int,
) -> float | None:
    """計算並回傳加班費，僅適用於 full_time 教師。非正職或無加班則回傳 None。

    此函式在建立預約時呼叫，將 overtime_pay 持久化到 bookings 表。
    """
    pool = supabase_service.pool

    # 確認是 full_time 合約
    tc = await pool.fetchrow(
        "SELECT employment_type FROM teacher_contracts WHERE id = $1",
        __import__('uuid').UUID(teacher_contract_id),
    )
    if not tc or tc["employment_type"] != "full_time":
        return None

    # 取得該 weekday 的工作時段
    weekday = booking_date.isoweekday() - 1  # 0=Mon, 6=Sun
    ws_rows = await pool.fetch(
        """SELECT start_time, end_time FROM teacher_work_schedules
           WHERE teacher_contract_id = $1 AND weekday = $2 AND is_deleted = FALSE""",
        __import__('uuid').UUID(teacher_contract_id), weekday,
    )
    work_slots = [(r["start_time"], r["end_time"]) for r in ws_rows]

    if work_slots:
        regular, overtime = calculate_regular_overtime_lessons(
            start_time, end_time, work_slots, course_duration,
        )
    else:
        # 該天無工作時段 → 全部視為加班
        overtime = calculate_lessons_used(start_time, end_time, course_duration)

    if overtime <= 0:
        return None

    # 取得加班費率
    ot_row = await pool.fetchrow(
        """SELECT amount FROM teacher_contract_details
           WHERE teacher_contract_id = $1 AND detail_type = 'overtime_rate' AND is_deleted = FALSE""",
        __import__('uuid').UUID(teacher_contract_id),
    )
    if not ot_row:
        return None

    return float(overtime * ot_row["amount"])


async def generate_booking_no() -> str:
    """生成預約編號: BK{YYYYMMDD}{序號}"""
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"BK{today}"

    # 查詢今天已有多少預約
    result = await supabase_service.table_select(
        table="bookings",
        select="booking_no",
        filters={"booking_no": f"like.{prefix}%"},
    )

    if not result:
        return f"{prefix}001"

    # 找出最大序號
    max_seq = 0
    for item in result:
        booking_no = item.get("booking_no", "")
        if booking_no.startswith(prefix):
            try:
                seq = int(booking_no[len(prefix):])
                max_seq = max(max_seq, seq)
            except ValueError:
                pass

    return f"{prefix}{str(max_seq + 1).zfill(3)}"


async def get_student_allowed_teachers(student_id: str) -> tuple[set[str] | None, bool]:
    """取得學生所有偏好設定的教師聯集（已優化：單次 SQL 取代三層巢狀迴圈）

    等級向下兼容：選 level 2 → 可選 level 1 和 2 的教師（teacher_level <= 偏好值）

    情境 1: primary_teacher_id 有值 → 直接加入該教師
    情境 2: course_id=NULL + min_teacher_level → 全域等級過濾（向下兼容）
    情境 3: course_id=X  + min_teacher_level → 指定課程等級過濾（向下兼容）

    Returns:
        (allowed_set, has_preferences)
    """
    pool = supabase_service.pool
    import uuid as _uuid
    sid = _uuid.UUID(student_id) if isinstance(student_id, str) else student_id

    all_prefs = await pool.fetch(
        """SELECT id, min_teacher_level, primary_teacher_id, course_id
           FROM student_teacher_preferences
           WHERE student_id = $1 AND is_deleted = FALSE""",
        sid,
    )

    if not all_prefs:
        return set(), False

    allowed: set[str] = set()

    # 分類偏好
    primary_ids = []
    global_min_levels = []
    course_prefs = []  # [(min_level, course_id)]

    for pref in all_prefs:
        primary = pref["primary_teacher_id"]
        min_level = pref["min_teacher_level"] or 1
        pref_course_id = pref["course_id"]

        if primary:
            primary_ids.append(primary)
        elif pref_course_id:
            course_prefs.append((min_level, pref_course_id))
        else:
            global_min_levels.append(min_level)

    # 情境 1: 指定教師 → 直接加入
    for pid in primary_ids:
        allowed.add(str(pid))

    # 情境 2: 全域等級過濾 → 一次查詢（向下兼容：等級 <= 偏好值）
    if global_min_levels:
        max_level_val = max(global_min_levels)  # 取最寬鬆的等級（向下兼容取最高）
        rows = await pool.fetch(
            """SELECT id FROM teachers
               WHERE is_deleted = FALSE AND is_active = TRUE AND teacher_level <= $1""",
            max_level_val,
        )
        for r in rows:
            allowed.add(str(r["id"]))

    # 情境 3: 指定課程 + 等級 → 單一 SQL 搞定（取代三層巢狀）
    if course_prefs:
        for min_level, cid in course_prefs:
            rows = await pool.fetch(
                """SELECT DISTINCT t.id
                   FROM teachers t
                   JOIN teacher_contracts tc ON tc.teacher_id = t.id
                       AND tc.is_deleted = FALSE AND tc.contract_status = 'active'
                   JOIN teacher_contract_details tcd ON tcd.teacher_contract_id = tc.id
                       AND tcd.course_id = $1 AND tcd.detail_type = 'course_rate'
                       AND tcd.is_deleted = FALSE
                   WHERE t.is_deleted = FALSE AND t.is_active = TRUE AND t.teacher_level <= $2""",
                cid, min_level,
            )
            for r in rows:
                allowed.add(str(r["id"]))

    return allowed, True


async def check_booking_overlap(
    teacher_slot_id: str,
    start_time: str,
    end_time: str,
    exclude_booking_id: str | None = None
) -> list[dict]:
    """檢查同一 slot 內是否有時間重疊的有效 booking

    Returns: 重疊的 booking 列表（空 = 無衝突）
    """
    # 查詢同 slot 的所有有效 booking（非已刪除、非已取消）
    existing_bookings = await supabase_service.table_select(
        table="bookings",
        select="id,start_time,end_time,booking_status",
        filters={
            "teacher_slot_id": f"eq.{teacher_slot_id}",
            "is_deleted": "eq.false",
        },
    )

    overlapping = []
    new_start = start_time[:5]  # HH:MM
    new_end = end_time[:5]

    for booking in existing_bookings:
        # 跳過已取消的
        if booking.get("booking_status") == "cancelled":
            continue
        # 跳過自己（用於更新場景）
        if exclude_booking_id and booking["id"] == exclude_booking_id:
            continue

        existing_start = booking.get("start_time", "")[:5]
        existing_end = booking.get("end_time", "")[:5]

        # 時間重疊判斷：new_start < existing_end AND new_end > existing_start
        if new_start < existing_end and new_end > existing_start:
            overlapping.append(booking)

    return overlapping


def generate_30min_blocks(slot_start: str, slot_end: str) -> list[dict]:
    """產生 30 分鐘區塊列表

    Args:
        slot_start: "HH:MM" or "HH:MM:SS" format
        slot_end: "HH:MM" or "HH:MM:SS" format
    Returns:
        list of {"start_time": time, "end_time": time}
    """
    start_parts = slot_start[:5].split(":")
    end_parts = slot_end[:5].split(":")
    start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
    end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])

    blocks = []
    current = start_minutes
    while current + 30 <= end_minutes:
        block_start = time(current // 60, current % 60)
        block_end = time((current + 30) // 60, (current + 30) % 60)
        blocks.append({"start_time": block_start, "end_time": block_end})
        current += 30

    return blocks


async def update_slot_booked_status(slot_id: str):
    """檢查 slot 的所有 30 分鐘區塊是否都已被預約，更新 is_booked 狀態

    - 所有區塊都被佔用 → is_booked = True（預約已滿）
    - 還有空閒區塊 → is_booked = False
    """
    # 取得 slot 資料
    slot = await supabase_service.table_select(
        table="teacher_available_slots",
        select="id,start_time,end_time",
        filters={"id": slot_id, "is_deleted": "eq.false"},
    )
    if not slot:
        return

    slot_start = slot[0].get("start_time", "")
    slot_end = slot[0].get("end_time", "")

    # 產生 30 分鐘區塊
    blocks = generate_30min_blocks(slot_start, slot_end)
    if not blocks:
        return

    # 取得該 slot 的所有有效 booking
    existing_bookings = await supabase_service.table_select(
        table="bookings",
        select="id,start_time,end_time,booking_status",
        filters={
            "teacher_slot_id": f"eq.{slot_id}",
            "is_deleted": "eq.false",
        },
    )

    active_bookings = [
        b for b in existing_bookings
        if b.get("booking_status") != "cancelled"
    ]

    # 檢查每個區塊是否都被覆蓋
    all_booked = True
    for block in blocks:
        block_start = block["start_time"].strftime("%H:%M")
        block_end = block["end_time"].strftime("%H:%M")

        block_covered = False
        for booking in active_bookings:
            b_start = booking.get("start_time", "")[:5]
            b_end = booking.get("end_time", "")[:5]
            if block_start >= b_start and block_end <= b_end:
                block_covered = True
                break

        if not block_covered:
            all_booked = False
            break

    # 更新 is_booked 狀態
    await supabase_service.table_update(
        table="teacher_available_slots",
        data={"is_booked": all_booked},
        filters={"id": slot_id},
    )


async def cancel_booking_side_effects(booking: dict):
    """取消預約的共用副作用：堂數歸還 + 時段釋放 + Zoom 取消

    Args:
        booking: 預約資料 dict，需含 id, lessons_used, student_contract_id, teacher_slot_id
    """
    booking_id = booking.get("id")
    booking_lessons = booking.get("lessons_used", 1)

    # 恢復學生合約剩餘堂數
    if booking.get("student_contract_id"):
        contract = await supabase_service.table_select(
            table="student_contracts",
            select="remaining_lessons",
            filters={"id": booking["student_contract_id"]},
        )
        if contract:
            await supabase_service.table_update(
                table="student_contracts",
                data={"remaining_lessons": contract[0]["remaining_lessons"] + booking_lessons},
                filters={"id": booking["student_contract_id"]},
            )

    # 更新 slot 預約已滿狀態
    if booking.get("teacher_slot_id"):
        await update_slot_booked_status(booking["teacher_slot_id"])

    # 取消 Zoom 會議
    if booking_id:
        try:
            from app.services.zoom_service import zoom_service
            from app.config import settings as app_settings
            if app_settings.zoom_enabled:
                asyncio.create_task(
                    zoom_service.cancel_meeting_for_booking(booking_id)
                )
        except Exception:
            pass


async def enrich_booking_with_relations(booking: dict) -> dict:
    """為預約資料添加關聯名稱"""
    # 取得學生名稱
    if booking.get("student_id"):
        student = await supabase_service.table_select(
            table="students",
            select="name",
            filters={"id": booking["student_id"]},
        )
        booking["student_name"] = student[0]["name"] if student else None

    # 取得教師名稱
    if booking.get("teacher_id"):
        teacher = await supabase_service.table_select(
            table="teachers",
            select="name",
            filters={"id": booking["teacher_id"]},
        )
        booking["teacher_name"] = teacher[0]["name"] if teacher else None

    # 計算 regular_lessons / overtime_minutes（從教師合約取得正職工作時段，依課程時長拆分）
    if booking.get("teacher_contract_id"):
        tc = await supabase_service.table_select(
            table="teacher_contracts",
            select="employment_type,work_start_time,work_end_time",
            filters={"id": booking["teacher_contract_id"]},
        )
        if tc and tc[0].get("employment_type") == "full_time":
            from datetime import time as dt_time

            # 取得課程 duration_minutes
            course_duration = 30  # fallback
            if booking.get("course_id"):
                course_info = await supabase_service.table_select(
                    table="courses", select="duration_minutes",
                    filters={"id": booking["course_id"]},
                )
                if course_info and course_info[0].get("duration_minutes"):
                    course_duration = course_info[0]["duration_minutes"]

            b_start = booking.get("start_time")
            b_end = booking.get("end_time")
            if isinstance(b_start, str):
                b_start = dt_time.fromisoformat(b_start)
            if isinstance(b_end, str):
                b_end = dt_time.fromisoformat(b_end)

            # 先查 teacher_work_schedules（依 booking_date 的 weekday）
            work_slots: list[tuple[time, time]] = []
            booking_date_str = booking.get("booking_date")
            if booking_date_str:
                from datetime import date as dt_date
                if isinstance(booking_date_str, str):
                    bd = dt_date.fromisoformat(booking_date_str)
                else:
                    bd = booking_date_str
                # Python isoweekday(): 1=Mon, 7=Sun → 轉為 0=Mon, 6=Sun
                weekday = bd.isoweekday() - 1

                schedules = await supabase_service.table_select(
                    table="teacher_work_schedules",
                    select="start_time,end_time",
                    filters={
                        "teacher_contract_id": f"eq.{booking['teacher_contract_id']}",
                        "weekday": f"eq.{weekday}",
                        "is_deleted": "eq.false"
                    },
                )
                for s in schedules:
                    ws = s["start_time"]
                    we = s["end_time"]
                    if isinstance(ws, str):
                        ws = dt_time.fromisoformat(ws)
                    if isinstance(we, str):
                        we = dt_time.fromisoformat(we)
                    work_slots.append((ws, we))

            # Fallback: 若無 work_schedules 資料，使用合約的 work_start_time/work_end_time
            if not work_slots and tc[0].get("work_start_time") and tc[0].get("work_end_time"):
                work_start = tc[0]["work_start_time"]
                work_end = tc[0]["work_end_time"]
                if isinstance(work_start, str):
                    work_start = dt_time.fromisoformat(work_start)
                if isinstance(work_end, str):
                    work_end = dt_time.fromisoformat(work_end)
                work_slots.append((work_start, work_end))

            if work_slots:
                regular, overtime = calculate_regular_overtime_lessons(
                    b_start, b_end, work_slots, course_duration
                )
            else:
                # 該天無工作時段 → 全部視為加班
                regular = 0
                overtime = calculate_lessons_used(b_start, b_end, course_duration)

            booking["regular_lessons"] = regular
            booking["overtime_lessons"] = overtime
            booking["is_overtime"] = overtime > 0

            # 加班費：優先使用 DB 持久化值，若無則動態計算
            if overtime > 0:
                if booking.get("overtime_pay") is not None:
                    pass  # 已從 DB 讀取
                elif booking.get("teacher_contract_id"):
                    ot_detail = await supabase_service.table_select(
                        table="teacher_contract_details",
                        select="amount",
                        filters={
                            "teacher_contract_id": f"eq.{booking['teacher_contract_id']}",
                            "detail_type": "eq.overtime_rate",
                            "is_deleted": "eq.false",
                        },
                    )
                    if ot_detail:
                        booking["overtime_pay"] = float(overtime * ot_detail[0]["amount"])

    # 取得課程名稱
    if booking.get("course_id"):
        course = await supabase_service.table_select(
            table="courses",
            select="course_name",
            filters={"id": booking["course_id"]},
        )
        booking["course_name"] = course[0]["course_name"] if course else None

    # 取得學生合約編號
    if booking.get("student_contract_id"):
        contract = await supabase_service.table_select(
            table="student_contracts",
            select="contract_no",
            filters={"id": booking["student_contract_id"]},
        )
        booking["student_contract_no"] = contract[0]["contract_no"] if contract else None

    # 取得教師合約編號
    if booking.get("teacher_contract_id"):
        contract = await supabase_service.table_select(
            table="teacher_contracts",
            select="contract_no",
            filters={"id": booking["teacher_contract_id"]},
        )
        booking["teacher_contract_no"] = contract[0]["contract_no"] if contract else None

    # 取得代課教師名稱
    if booking.get("substitute_detail_id"):
        sub = await supabase_service.table_select(
            table="substitute_details",
            select="substitute_teacher_id",
            filters={"id": booking["substitute_detail_id"], "is_deleted": "eq.false"},
        )
        if sub:
            sub_teacher = await supabase_service.table_select(
                table="teachers",
                select="name",
                filters={"id": sub[0]["substitute_teacher_id"]},
            )
            booking["substitute_teacher_name"] = sub_teacher[0]["name"] if sub_teacher else None
        else:
            booking["substitute_teacher_name"] = None
    else:
        booking["substitute_teacher_name"] = None

    # 檢查是否有 pending 的請假紀錄
    leave_check = await supabase_service.table_select(
        table="leave_records",
        select="id,initiator_type",
        filters={
            "booking_id": f"eq.{booking['id']}",
            "leave_status": "eq.pending",
            "is_deleted": "eq.false",
        },
    )
    booking["has_pending_leave"] = len(leave_check) > 0
    booking["pending_leave_initiator_type"] = leave_check[0]["initiator_type"] if leave_check else None

    return booking


@router.get("", response_model=BookingListResponse)
async def list_bookings(
    page: int = Query(1, ge=1, description="頁碼"),
    per_page: int = Query(20, ge=1, le=100, description="每頁數量"),
    search: Optional[str] = Query(None, description="搜尋預約編號"),
    booking_status: Optional[BookingStatus] = Query(None, description="篩選預約狀態"),
    student_id: Optional[str] = Query(None, description="篩選學生"),
    teacher_id: Optional[str] = Query(None, description="篩選教師"),
    course_id: Optional[str] = Query(None, description="篩選課程"),
    date_from: Optional[date] = Query(None, description="開始日期"),
    date_to: Optional[date] = Query(None, description="結束日期"),
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得預約列表（已優化：單一 JOIN 查詢取代 N+1 enrich 迴圈）"""
    try:
        pool = supabase_service.pool

        # ── 動態 WHERE 條件 ──
        conditions = ["b.is_deleted = FALSE"]
        params: list = []
        idx = 0

        if booking_status:
            idx += 1
            conditions.append(f"b.booking_status = ${idx}")
            params.append(booking_status.value)
        if student_id:
            idx += 1
            conditions.append(f"b.student_id = ${idx}")
            params.append(__import__('uuid').UUID(student_id))
        if teacher_id:
            idx += 1
            conditions.append(f"b.teacher_id = ${idx}")
            params.append(__import__('uuid').UUID(teacher_id))
        if course_id:
            idx += 1
            conditions.append(f"b.course_id = ${idx}")
            params.append(__import__('uuid').UUID(course_id))
        if date_from:
            idx += 1
            conditions.append(f"b.booking_date >= ${idx}")
            params.append(date_from)
        if date_to:
            idx += 1
            conditions.append(f"b.booking_date <= ${idx}")
            params.append(date_to)
        if search:
            idx += 1
            conditions.append(f"b.booking_no ILIKE ${idx}")
            params.append(f"%{search}%")

        # 角色過濾
        if current_user.is_student() and current_user.student_id:
            idx += 1
            conditions.append(f"b.student_id = ${idx}")
            params.append(__import__('uuid').UUID(current_user.student_id))
        elif current_user.is_teacher() and current_user.teacher_id:
            # 教師可看到自己的預約 + 被指派為代課教師的預約
            teacher_uuid = __import__('uuid').UUID(current_user.teacher_id)
            idx += 1
            t_idx = idx
            idx += 1
            st_idx = idx
            conditions.append(
                f"(b.teacher_id = ${t_idx} OR EXISTS("
                f"SELECT 1 FROM substitute_details sd2 "
                f"WHERE sd2.booking_id = b.id AND sd2.substitute_teacher_id = ${st_idx} "
                f"AND sd2.is_deleted = FALSE))"
            )
            params.extend([teacher_uuid, teacher_uuid])

        where_sql = " AND ".join(conditions)

        # ── COUNT ──
        count_sql = f"SELECT COUNT(*) FROM bookings b WHERE {where_sql}"
        total = await pool.fetchval(count_sql, *params)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset_val = (page - 1) * per_page

        # ── 主查詢：一次 JOIN 帶出所有關聯名稱 ──
        idx += 1
        limit_idx = idx
        idx += 1
        offset_idx = idx
        params.extend([per_page, offset_val])

        data_sql = f"""
            SELECT b.id, b.booking_no, b.student_id, b.teacher_id, b.course_id,
                   b.student_contract_id, b.teacher_contract_id, b.teacher_slot_id,
                   b.substitute_detail_id, b.teacher_hourly_rate, b.teacher_rate_percentage,
                   b.booking_status, b.booking_type, b.booking_date, b.start_time, b.end_time,
                   b.lessons_used, b.overtime_pay, b.notes, b.created_at, b.updated_at,
                   -- is_trial_to_formal (from bookings_view logic)
                   EXISTS(SELECT 1 FROM teacher_bonus_records tbr
                          WHERE tbr.related_booking_id = b.id AND tbr.bonus_type = 'trial_to_formal'
                            AND tbr.is_deleted = FALSE) AS is_trial_to_formal,
                   -- 關聯名稱
                   s.name AS student_name,
                   t.name AS teacher_name,
                   c.course_name AS course_name,
                   c.duration_minutes,
                   sc.contract_no AS student_contract_no,
                   tc.contract_no AS teacher_contract_no,
                   tc.employment_type,
                   -- 代課教師
                   sub_t.name AS substitute_teacher_name,
                   -- 待審請假
                   lv.has_pending_leave,
                   lv.pending_leave_initiator_type
            FROM bookings b
            LEFT JOIN students s ON s.id = b.student_id
            LEFT JOIN teachers t ON t.id = b.teacher_id
            LEFT JOIN courses c ON c.id = b.course_id
            LEFT JOIN student_contracts sc ON sc.id = b.student_contract_id
            LEFT JOIN teacher_contracts tc ON tc.id = b.teacher_contract_id
            LEFT JOIN substitute_details sd ON sd.id = b.substitute_detail_id AND sd.is_deleted = FALSE
            LEFT JOIN teachers sub_t ON sub_t.id = sd.substitute_teacher_id
            LEFT JOIN LATERAL (
                SELECT TRUE AS has_pending_leave, lr.initiator_type AS pending_leave_initiator_type
                FROM leave_records lr
                WHERE lr.booking_id = b.id AND lr.leave_status = 'pending' AND lr.is_deleted = FALSE
                LIMIT 1
            ) lv ON TRUE
            WHERE {where_sql}
            ORDER BY b.booking_date DESC, b.start_time DESC
            LIMIT ${limit_idx} OFFSET ${offset_idx}
        """

        rows = await pool.fetch(data_sql, *params)

        # ── 批次計算正班/加班（僅 full_time 教師） ──
        ft_bookings = []  # 需要計算 overtime 的預約 index
        tc_ids = set()
        for i, row in enumerate(rows):
            if row["employment_type"] == "full_time":
                ft_bookings.append(i)
                tc_ids.add(row["teacher_contract_id"])

        # 批次取得工作時段
        work_schedule_map: dict = {}  # {teacher_contract_id: {weekday: [(start, end)]}}
        overtime_rate_map: dict = {}  # {teacher_contract_id: amount}
        if tc_ids:
            tc_id_list = list(tc_ids)
            ws_rows = await pool.fetch(
                """SELECT teacher_contract_id, weekday, start_time, end_time
                   FROM teacher_work_schedules
                   WHERE teacher_contract_id = ANY($1) AND is_deleted = FALSE""",
                tc_id_list,
            )
            for ws in ws_rows:
                key = str(ws["teacher_contract_id"])
                if key not in work_schedule_map:
                    work_schedule_map[key] = {}
                wd = ws["weekday"]
                if wd not in work_schedule_map[key]:
                    work_schedule_map[key][wd] = []
                work_schedule_map[key][wd].append((ws["start_time"], ws["end_time"]))

            # 批次取得加班費率
            ot_rows = await pool.fetch(
                """SELECT teacher_contract_id, amount
                   FROM teacher_contract_details
                   WHERE teacher_contract_id = ANY($1)
                     AND detail_type = 'overtime_rate'
                     AND is_deleted = FALSE""",
                tc_id_list,
            )
            for ot in ot_rows:
                overtime_rate_map[str(ot["teacher_contract_id"])] = float(ot["amount"])

        # ── 組裝結果 ──
        enriched_bookings = []
        for i, row in enumerate(rows):
            b = dict(row)
            b["id"] = str(b["id"])
            if b.get("student_id"): b["student_id"] = str(b["student_id"])
            if b.get("teacher_id"): b["teacher_id"] = str(b["teacher_id"])
            if b.get("course_id"): b["course_id"] = str(b["course_id"])
            if b.get("student_contract_id"): b["student_contract_id"] = str(b["student_contract_id"])
            if b.get("teacher_contract_id"): b["teacher_contract_id"] = str(b["teacher_contract_id"])
            if b.get("teacher_slot_id"): b["teacher_slot_id"] = str(b["teacher_slot_id"])
            if b.get("substitute_detail_id"): b["substitute_detail_id"] = str(b["substitute_detail_id"])
            b["has_pending_leave"] = b.get("has_pending_leave") or False
            b.pop("duration_minutes", None)
            b.pop("employment_type", None)

            # 正班/加班計算
            if i in ft_bookings:
                tc_key = str(row["teacher_contract_id"])
                booking_date_val = row["booking_date"]
                weekday = booking_date_val.isoweekday() - 1 if booking_date_val else None
                work_slots = work_schedule_map.get(tc_key, {}).get(weekday, []) if weekday is not None else []
                duration = row["duration_minutes"] or 30
                if row["start_time"] and row["end_time"]:
                    if work_slots:
                        regular, overtime = calculate_regular_overtime_lessons(
                            row["start_time"], row["end_time"], work_slots, duration
                        )
                    else:
                        # 該天無工作時段 → 全部視為加班
                        regular = 0
                        overtime = calculate_lessons_used(row["start_time"], row["end_time"], duration)
                    b["regular_lessons"] = regular
                    b["overtime_lessons"] = overtime
                    b["is_overtime"] = overtime > 0
                    # 加班費：優先使用 DB 持久化值，若無則動態計算
                    if overtime > 0:
                        if b.get("overtime_pay") is None and tc_key in overtime_rate_map:
                            b["overtime_pay"] = overtime * overtime_rate_map[tc_key]

            enriched_bookings.append(b)

        return BookingListResponse(
            data=[BookingResponse(**b) for b in enriched_bookings],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得預約列表失敗: {str(e)}")


@router.get("/slot-availability/{teacher_slot_id}", response_model=DataResponse[SlotAvailabilityResponse])
async def get_slot_availability(
    teacher_slot_id: str,
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得指定教師時段的 30 分鐘區塊可用狀態"""
    try:
        # 取得時段資料
        slot = await supabase_service.table_select(
            table="teacher_available_slots",
            select="id,slot_date,start_time,end_time,is_available",
            filters={"id": teacher_slot_id, "is_deleted": "eq.false"},
        )

        if not slot:
            raise HTTPException(status_code=404, detail="教師時段不存在")

        slot_data = slot[0]
        slot_start = slot_data.get("start_time", "")
        slot_end = slot_data.get("end_time", "")

        # 產生 30 分鐘區塊
        blocks = generate_30min_blocks(slot_start, slot_end)

        # 取得該 slot 的所有有效 booking
        existing_bookings = await supabase_service.table_select(
            table="bookings",
            select="id,start_time,end_time,booking_status",
            filters={
                "teacher_slot_id": f"eq.{teacher_slot_id}",
                "is_deleted": "eq.false",
            },
        )

        # 過濾掉已取消的
        active_bookings = [
            b for b in existing_bookings
            if b.get("booking_status") != "cancelled"
        ]

        # 標記每個區塊的狀態
        result_blocks = []
        for block in blocks:
            block_start = block["start_time"].strftime("%H:%M")
            block_end = block["end_time"].strftime("%H:%M")

            is_available = True
            booking_id = None

            for booking in active_bookings:
                b_start = booking.get("start_time", "")[:5]
                b_end = booking.get("end_time", "")[:5]

                # 區塊被 booking 覆蓋：block_start >= b_start AND block_end <= b_end
                if block_start >= b_start and block_end <= b_end:
                    is_available = False
                    booking_id = booking["id"]
                    break

            result_blocks.append(TimeBlock(
                start_time=block["start_time"],
                end_time=block["end_time"],
                is_available=is_available,
                booking_id=booking_id
            ))

        slot_date = date.fromisoformat(slot_data["slot_date"])
        return DataResponse(data=SlotAvailabilityResponse(
            slot_id=teacher_slot_id,
            slot_date=slot_date,
            slot_start_time=time.fromisoformat(slot_start[:5]),
            slot_end_time=time.fromisoformat(slot_end[:5]),
            blocks=result_blocks
        ))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得時段可用狀態失敗: {str(e)}")


@router.get("/my-student-info", tags=["預約管理"])
async def get_my_student_info(
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得當前用戶的學生資料（學生用）"""
    try:
        user_student_id = current_user.student_id

        if not user_student_id:
            return {"data": None}

        student = await supabase_service.table_select(
            table="students",
            select="id,student_no,name,student_type",
            filters={"id": user_student_id, "is_deleted": "eq.false"},
        )

        if not student:
            return {"data": None}

        return {"data": student[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-contracts", tags=["預約管理"])
async def get_my_contracts(
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得當前學生的合約（學生用，按建立時間由新到舊排序）"""
    try:
        user_student_id = current_user.student_id

        if not user_student_id:
            return {"data": []}

        contracts = await supabase_service.table_select(
            table="student_contracts",
            select="id,contract_no,remaining_lessons,created_at",
            filters={
                "student_id": user_student_id,
                "is_deleted": "eq.false",
                "contract_status": "eq.active"
            },
        )

        # 按 created_at 降序排列（最新的在前）
        contracts.sort(key=lambda c: c.get("created_at", ""), reverse=True)

        # 從合約明細取得關聯課程
        enriched = []
        for contract in contracts:
            details = await supabase_service.table_select(
                table="student_contract_details",
                select="course_id",
                filters={
                    "student_contract_id": contract["id"],
                    "detail_type": "eq.lesson_price",
                    "is_deleted": "eq.false"
                },
            )
            course_ids = list(set(d["course_id"] for d in details if d.get("course_id")))
            course_names = []
            first_course_id = course_ids[0] if course_ids else None
            for cid in course_ids:
                c = await supabase_service.table_select(
                    table="courses",
                    select="course_name",
                    filters={"id": cid},
                )
                if c:
                    course_names.append(c[0]["course_name"])
            contract["course_id"] = first_course_id
            contract["course_ids"] = course_ids
            contract["course_name"] = ", ".join(course_names) if course_names else None
            enriched.append(contract)

        return {"data": enriched}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{booking_id}", response_model=DataResponse[BookingResponse])
async def get_booking(
    booking_id: str,
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得單一預約"""
    try:
        result = await supabase_service.table_select(
            table="bookings_view",
            select="id,booking_no,student_id,teacher_id,course_id,student_contract_id,teacher_contract_id,teacher_slot_id,substitute_detail_id,teacher_hourly_rate,teacher_rate_percentage,booking_status,booking_type,is_trial_to_formal,booking_date,start_time,end_time,notes,created_at,updated_at",
            filters={"id": booking_id, "is_deleted": "eq.false"},
        )

        if not result:
            raise HTTPException(status_code=404, detail="預約不存在")

        # Ownership check: 學生/教師只能查自己的預約（含代課教師）
        if current_user.is_student():
            if result[0].get("student_id") != current_user.student_id:
                raise HTTPException(status_code=403, detail="無權查看此預約")
        elif current_user.is_teacher():
            is_original = result[0].get("teacher_id") == current_user.teacher_id
            is_substitute = False
            if result[0].get("substitute_detail_id"):
                sd = await supabase_service.table_select(
                    table="substitute_details", select="substitute_teacher_id",
                    filters={"id": result[0]["substitute_detail_id"], "is_deleted": "eq.false"},
                )
                is_substitute = bool(sd and sd[0].get("substitute_teacher_id") == current_user.teacher_id)
            if not (is_original or is_substitute):
                raise HTTPException(status_code=403, detail="無權查看此預約")

        booking = await enrich_booking_with_relations(result[0])
        return DataResponse(data=BookingResponse(**booking))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得預約失敗: {str(e)}")


@router.post("", response_model=DataResponse[BookingResponse])
async def create_booking(
    data: BookingCreate,
    current_user: CurrentUser = Depends(require_page_permission("bookings.create"))
):
    """建立預約（員工可為任何學生預約，學生只能為自己預約）"""
    try:
        # 權限檢查
        if current_user.is_student():
            # 學生只能為自己預約
            if not current_user.student_id:
                raise HTTPException(status_code=403, detail="無法取得學生資料")
            if data.student_id != current_user.student_id:
                raise HTTPException(status_code=403, detail="學生只能為自己預約")
        elif not current_user.is_staff():
            # 教師和其他角色不能建立預約
            raise HTTPException(status_code=403, detail="無權建立預約")

        # 驗證學生存在
        student = await supabase_service.table_select(
            table="students",
            select="id,name,student_type",
            filters={"id": data.student_id, "is_deleted": "eq.false"},
        )
        if not student:
            raise HTTPException(status_code=400, detail="學生不存在")

        is_trial = student[0].get("student_type") == "trial"

        # 驗證教師存在
        teacher = await supabase_service.table_select(
            table="teachers",
            select="id,name,teacher_level",
            filters={"id": data.teacher_id, "is_deleted": "eq.false"},
        )
        if not teacher:
            raise HTTPException(status_code=400, detail="教師不存在")

        # 驗證課程存在
        course = await supabase_service.table_select(
            table="courses",
            select="id,course_name,duration_minutes",
            filters={"id": data.course_id, "is_deleted": "eq.false"},
        )
        if not course:
            raise HTTPException(status_code=400, detail="課程不存在")

        # 驗證預約時長是課程時長的倍數
        course_duration = course[0].get("duration_minutes", 60)
        start_minutes = data.start_time.hour * 60 + data.start_time.minute
        end_minutes = data.end_time.hour * 60 + data.end_time.minute
        booking_minutes = end_minutes - start_minutes
        if booking_minutes % course_duration != 0:
            raise HTTPException(
                status_code=400,
                detail=f"預約時長 ({booking_minutes}分鐘) 必須是課程時長 ({course_duration}分鐘) 的倍數"
            )
        lessons_used = calculate_lessons_used(data.start_time, data.end_time, course_duration)

        # 驗證課程交集合法性：學生選課 ∩ 教師可教課程
        # (a) 非 trial 學生：驗證 student_courses 有此 course_id
        if not is_trial:
            sc_check = await supabase_service.table_select(
                table="student_courses",
                select="id",
                filters={
                    "student_id": data.student_id,
                    "course_id": data.course_id,
                    "is_deleted": "eq.false"
                },
            )
            if not sc_check:
                raise HTTPException(status_code=400, detail="學生未選修此課程")

        # (b) 所有情況：驗證老師有此課程的 course_rate
        teacher_active_contracts = await supabase_service.table_select(
            table="teacher_contracts",
            select="id",
            filters={
                "teacher_id": data.teacher_id,
                "is_deleted": "eq.false",
                "contract_status": "eq.active"
            },
        )
        has_course_rate = False
        for tc in teacher_active_contracts:
            rate_check = await supabase_service.table_select(
                table="teacher_contract_details",
                select="id",
                filters={
                    "teacher_contract_id": tc["id"],
                    "course_id": data.course_id,
                    "detail_type": "eq.course_rate",
                    "is_deleted": "eq.false"
                },
            )
            if rate_check:
                has_course_rate = True
                break
        if not has_course_rate:
            raise HTTPException(status_code=400, detail="教師無此課程的授課資格")

        # 驗證教師是否在學生偏好的可預約教師白名單內
        allowed_set, _ = await get_student_allowed_teachers(data.student_id)
        if data.teacher_id not in allowed_set:
            raise HTTPException(
                status_code=400,
                detail="此教師不在學生的偏好可預約教師範圍內，請先設定教師偏好"
            )

        # 驗證學生合約存在且有效（試上學生可不提供合約）
        student_contract = None
        if data.student_contract_id:
            student_contract = await supabase_service.table_select(
                table="student_contracts",
                select="id,contract_no,remaining_lessons",
                filters={"id": data.student_contract_id, "is_deleted": "eq.false"},
            )
            if not student_contract:
                raise HTTPException(status_code=400, detail="學生合約不存在")
            if student_contract[0].get("remaining_lessons", 0) < lessons_used:
                raise HTTPException(status_code=400, detail=f"學生合約剩餘堂數不足（需要 {lessons_used} 堂）")
        elif not is_trial:
            raise HTTPException(status_code=400, detail="正式學生必須提供學生合約")

        # 驗證教師合約存在且取得時薪（如果有提供）
        teacher_contract_id = data.teacher_contract_id
        hourly_rate = 0
        rate_percentage = None

        if teacher_contract_id:
            teacher_contract = await supabase_service.table_select(
                table="teacher_contracts",
                select="id,contract_no",
                filters={"id": teacher_contract_id, "is_deleted": "eq.false"},
            )
            if not teacher_contract:
                raise HTTPException(status_code=400, detail="教師合約不存在")

            # 取得教師時薪（從 teacher_contract_details）
            teacher_rate = await supabase_service.table_select(
                table="teacher_contract_details",
                select="amount",
                filters={
                    "teacher_contract_id": teacher_contract_id,
                    "course_id": data.course_id,
                    "detail_type": "eq.course_rate",
                    "is_deleted": "eq.false"
                },
            )
            if teacher_rate:
                hourly_rate = teacher_rate[0].get("amount", 0)

        # 處理教師時段：如果提供了 slot_id 則驗證，否則自動尋找
        teacher_slot_id = data.teacher_slot_id
        booking_start = data.start_time.isoformat()[:5]  # HH:MM
        booking_end = data.end_time.isoformat()[:5]  # HH:MM

        if teacher_slot_id:
            # 驗證指定的時段存在且可用
            teacher_slot = await supabase_service.table_select(
                table="teacher_available_slots",
                select="id,slot_date,start_time,end_time,is_available,teacher_contract_id",
                filters={"id": teacher_slot_id, "is_deleted": "eq.false"},
            )
            if not teacher_slot:
                raise HTTPException(status_code=400, detail="教師時段不存在")
            if not teacher_slot[0].get("is_available"):
                raise HTTPException(status_code=400, detail="教師時段不可用")

            # 驗證預約時間落在時段區間內
            slot_date = teacher_slot[0].get("slot_date", "")
            slot_start = teacher_slot[0].get("start_time", "")[:5]
            slot_end = teacher_slot[0].get("end_time", "")[:5]

            if slot_date != data.booking_date.isoformat():
                raise HTTPException(status_code=400, detail="預約日期與時段日期不符")
            if booking_start < slot_start or booking_end > slot_end:
                raise HTTPException(
                    status_code=400,
                    detail=f"預約時間 ({booking_start}-{booking_end}) 超出時段範圍 ({slot_start}-{slot_end})"
                )

            # 檢查時間重疊
            overlapping = await check_booking_overlap(teacher_slot_id, booking_start, booking_end)
            if overlapping:
                raise HTTPException(
                    status_code=409,
                    detail=f"預約時間 ({booking_start}-{booking_end}) 與現有預約衝突"
                )

            # 使用時段的教師合約（如果沒有指定）
            if not teacher_contract_id and teacher_slot[0].get("teacher_contract_id"):
                teacher_contract_id = teacher_slot[0]["teacher_contract_id"]

        else:
            # 自動尋找包含預約時間的可用時段
            all_slots = await supabase_service.table_select(
                table="teacher_available_slots",
                select="id,slot_date,start_time,end_time,is_available,teacher_contract_id",
                filters={
                    "teacher_id": f"eq.{data.teacher_id}",
                    "slot_date": f"eq.{data.booking_date.isoformat()}",
                    "is_deleted": "eq.false",
                    "is_available": "eq.true",
                },
            )

            # 找出包含預約時間區間的時段，並檢查無重疊
            matching_slot = None
            for slot in all_slots:
                slot_start = slot.get("start_time", "")[:5]
                slot_end = slot.get("end_time", "")[:5]

                # 檢查預約時間是否落在時段區間內
                if booking_start >= slot_start and booking_end <= slot_end:
                    # 檢查是否有重疊
                    overlapping = await check_booking_overlap(slot["id"], booking_start, booking_end)
                    if not overlapping:
                        matching_slot = slot
                        break

            if not matching_slot:
                raise HTTPException(
                    status_code=400,
                    detail=f"找不到包含預約時間 ({booking_start}-{booking_end}) 的可用時段，或時段內該時間已被預約"
                )

            teacher_slot_id = matching_slot["id"]

            # 使用時段的教師合約（如果沒有指定）
            if not teacher_contract_id and matching_slot.get("teacher_contract_id"):
                teacher_contract_id = matching_slot["teacher_contract_id"]

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        # 計算加班費（正職教師才有）
        overtime_pay_val = None
        if teacher_contract_id and not is_trial:
            overtime_pay_val = await compute_overtime_pay(
                teacher_contract_id, data.booking_date,
                data.start_time, data.end_time, course_duration,
            )

        # ── 交易區段：鎖定時段 + 重新檢查衝突 + 寫入 ──
        # 使用 database transaction 防止同一時段被並發預約
        async with supabase_service.pool.acquire() as conn:
            async with conn.transaction():
                # 鎖定教師時段（FOR UPDATE 防止並發）
                slot_lock = await conn.fetchrow(
                    "SELECT id FROM teacher_available_slots WHERE id = $1 FOR UPDATE",
                    uuid.UUID(teacher_slot_id)
                )
                if not slot_lock:
                    raise HTTPException(status_code=400, detail="教師時段不存在")

                # 在交易內重新檢查時間衝突（確保無 race condition）
                overlap_rows = await conn.fetch(
                    """SELECT id FROM bookings
                       WHERE teacher_slot_id = $1
                       AND is_deleted = false
                       AND booking_status != 'cancelled'
                       AND start_time::time < $3::time
                       AND end_time::time > $2::time""",
                    uuid.UUID(teacher_slot_id),
                    data.start_time,
                    data.end_time
                )
                if overlap_rows:
                    raise HTTPException(
                        status_code=409,
                        detail=f"預約時間 ({booking_start}-{booking_end}) 與現有預約衝突"
                    )

                # 在交易內生成預約編號（防止序號衝突）
                today = datetime.utcnow().strftime("%Y%m%d")
                prefix = f"BK{today}"
                seq_row = await conn.fetchrow(
                    """SELECT booking_no FROM bookings
                       WHERE booking_no LIKE $1
                       ORDER BY booking_no DESC LIMIT 1""",
                    f"{prefix}%"
                )
                if seq_row:
                    try:
                        max_seq = int(seq_row["booking_no"][len(prefix):])
                    except ValueError:
                        max_seq = 0
                    booking_no = f"{prefix}{str(max_seq + 1).zfill(3)}"
                else:
                    booking_no = f"{prefix}001"

                # 寫入預約
                result_row = await conn.fetchrow(
                    """INSERT INTO bookings (
                        booking_no, student_id, teacher_id, course_id,
                        student_contract_id, teacher_contract_id, teacher_slot_id,
                        teacher_hourly_rate, teacher_rate_percentage,
                        booking_status, booking_date, start_time, end_time,
                        booking_type, lessons_used, overtime_pay, notes, created_by
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
                    ) RETURNING *""",
                    booking_no,
                    uuid.UUID(data.student_id),
                    uuid.UUID(data.teacher_id),
                    uuid.UUID(data.course_id),
                    uuid.UUID(data.student_contract_id) if data.student_contract_id else None,
                    uuid.UUID(teacher_contract_id) if teacher_contract_id else None,
                    uuid.UUID(teacher_slot_id),
                    0 if is_trial else hourly_rate,
                    rate_percentage,
                    "pending",
                    data.booking_date,
                    data.start_time,
                    data.end_time,
                    "trial" if is_trial else "regular",
                    lessons_used,
                    overtime_pay_val,
                    data.notes,
                    uuid.UUID(employee_id) if employee_id else None,
                )

                if not result_row:
                    raise HTTPException(status_code=500, detail="建立預約失敗")

                # 扣除學生合約剩餘堂數
                if student_contract and data.student_contract_id:
                    await conn.execute(
                        "UPDATE student_contracts SET remaining_lessons = remaining_lessons - $1 WHERE id = $2",
                        lessons_used,
                        uuid.UUID(data.student_contract_id)
                    )

                # 更新 slot 預約已滿狀態
                booked_count = await conn.fetchval(
                    """SELECT COUNT(*) FROM bookings
                       WHERE teacher_slot_id = $1 AND is_deleted = false AND booking_status != 'cancelled'""",
                    uuid.UUID(teacher_slot_id)
                )
                slot_info = await conn.fetchrow(
                    "SELECT start_time, end_time FROM teacher_available_slots WHERE id = $1",
                    uuid.UUID(teacher_slot_id)
                )
                if slot_info:
                    slot_duration = (datetime.combine(date.today(), slot_info["end_time"]) -
                                    datetime.combine(date.today(), slot_info["start_time"])).total_seconds() / 60
                    max_bookings = max(1, int(slot_duration / course_duration))
                    is_fully_booked = booked_count >= max_bookings
                    await conn.execute(
                        "UPDATE teacher_available_slots SET is_booked = $1 WHERE id = $2",
                        is_fully_booked,
                        uuid.UUID(teacher_slot_id)
                    )

        # 交易結束後：enrichment（只需讀取，不需在交易內）
        result = dict(result_row)
        # 轉換 UUID 為字串
        for key, val in result.items():
            if isinstance(val, uuid.UUID):
                result[key] = str(val)
            elif isinstance(val, (date, datetime)):
                result[key] = val.isoformat()
            elif isinstance(val, time):
                result[key] = val.isoformat()

        enriched = await enrich_booking_with_relations(result)

        return DataResponse(
            message="預約建立成功",
            data=BookingResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立預約失敗: {str(e)}")


@router.put("/batch", response_model=BaseResponse)
async def batch_update_bookings(
    data: BookingBatchUpdate,
    current_user: CurrentUser = Depends(require_page_permission("bookings.edit"))
):
    """批次更新預約狀態（週期性篩選，僅限員工）"""
    try:
        # 查詢符合條件的預約
        filters = {"is_deleted": "eq.false"}

        if data.student_id:
            filters["student_id"] = f"eq.{data.student_id}"
        if data.teacher_id:
            filters["teacher_id"] = f"eq.{data.teacher_id}"
        if data.course_id:
            filters["course_id"] = f"eq.{data.course_id}"
        if data.filter_status:
            filters["booking_status"] = f"eq.{data.filter_status.value}"

        all_bookings = await supabase_service.table_select(
            table="bookings",
            select="id,booking_date,booking_status,teacher_slot_id,student_contract_id,lessons_used",
            filters=filters,
        )

        # 在 Python 中進行更精細的過濾
        bookings_to_update = []
        for booking in all_bookings:
            booking_date_str = booking.get("booking_date", "")
            booking_date_obj = date.fromisoformat(booking_date_str) if booking_date_str else None

            if not booking_date_obj:
                continue

            # 檢查日期範圍
            if booking_date_obj < data.start_date or booking_date_obj > data.end_date:
                continue

            # 檢查星期幾
            if data.weekdays is not None and booking_date_obj.weekday() not in data.weekdays:
                continue

            bookings_to_update.append(booking)

        if not bookings_to_update:
            return BaseResponse(message="沒有符合條件的預約可更新")

        # 批次更新
        updated_count = 0
        restored_contracts = []
        affected_slot_ids = set()

        for booking in bookings_to_update:
            old_status = booking.get("booking_status")

            # 已取消的預約不可修改
            if old_status == "cancelled":
                continue

            # 準備更新資料
            update_data = {"booking_status": data.new_status.value}
            if data.notes is not None:
                update_data["notes"] = data.notes

            result = await supabase_service.table_update(
                table="bookings",
                data=update_data,
                filters={"id": booking["id"]},
            )

            if result:
                updated_count += 1

                # 如果狀態變更為取消，恢復堂數
                if data.new_status.value == "cancelled" and old_status != "cancelled":
                    booking_lessons = booking.get("lessons_used", 1)
                    # 恢復學生合約剩餘堂數
                    contract = await supabase_service.table_select(
                        table="student_contracts",
                        select="remaining_lessons",
                        filters={"id": booking["student_contract_id"]},
                    )
                    if contract:
                        await supabase_service.table_update(
                            table="student_contracts",
                            data={"remaining_lessons": contract[0]["remaining_lessons"] + booking_lessons},
                            filters={"id": booking["student_contract_id"]},
                        )
                        restored_contracts.append(booking["student_contract_id"])

                    if booking.get("teacher_slot_id"):
                        affected_slot_ids.add(booking["teacher_slot_id"])

        # 更新所有受影響 slot 的預約已滿狀態
        for sid in affected_slot_ids:
            await update_slot_booked_status(sid)

        message = f"已更新 {updated_count} 筆預約"
        if restored_contracts:
            message += f"，恢復 {len(restored_contracts)} 份合約堂數"

        return BaseResponse(message=message)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次更新預約失敗: {str(e)}")


@router.put("/{booking_id}", response_model=DataResponse[BookingResponse])
async def update_booking(
    booking_id: str,
    data: BookingUpdate,
    current_user: CurrentUser = Depends(require_page_permission("bookings.edit"))
):
    """更新預約（員工可完整更新，教師僅可將自己的預約確認）"""
    try:
        # 檢查預約是否存在
        existing = await supabase_service.table_select(
            table="bookings",
            select="id,booking_status,teacher_slot_id,student_contract_id,teacher_id,student_id,lessons_used,start_time,end_time,course_id,booking_type,teacher_contract_id",
            filters={"id": booking_id, "is_deleted": "eq.false"},
        )

        if not existing:
            raise HTTPException(status_code=404, detail="預約不存在")

        old_status = existing[0].get("booking_status")

        # 教師權限：僅能將自己的預約狀態改為 confirmed
        if current_user.is_teacher():
            if existing[0].get("teacher_id") != current_user.teacher_id:
                raise HTTPException(status_code=403, detail="教師只能更新自己的預約")
            if not data.booking_status or data.booking_status.value != "confirmed":
                raise HTTPException(status_code=403, detail="教師僅可將預約狀態更新為已確認")
            if old_status != "pending":
                raise HTTPException(status_code=400, detail="只有待確認的預約可以確認")
        elif current_user.is_student():
            raise HTTPException(status_code=403, detail="學生無權更新預約")

        # 非管理員：已完成的預約不可修改
        if old_status == "completed" and not current_user.is_admin():
            raise HTTPException(status_code=400, detail="已完成的預約無法修改，僅管理員可變更")

        # 已取消的預約不可修改（管理員除外）
        if old_status == "cancelled" and not current_user.is_admin():
            raise HTTPException(status_code=400, detail="已取消的預約無法修改，僅管理員可變更")

        # 處理 end_time 縮短預約
        end_time_delta = 0  # 要退回的堂數差額
        if data.end_time is not None:
            # 驗證 30 分鐘邊界
            if data.end_time.minute not in (0, 30) or data.end_time.second != 0:
                raise HTTPException(status_code=400, detail="結束時間必須在 30 分鐘邊界上")

            orig_start_str = existing[0].get("start_time", "")
            orig_end_str = existing[0].get("end_time", "")
            orig_start = time.fromisoformat(orig_start_str) if isinstance(orig_start_str, str) else orig_start_str
            orig_end = time.fromisoformat(orig_end_str) if isinstance(orig_end_str, str) else orig_end_str

            if data.end_time <= orig_start:
                raise HTTPException(status_code=400, detail="新結束時間必須晚於開始時間")
            if data.end_time > orig_end:
                raise HTTPException(status_code=400, detail="只允許縮短預約（新結束時間不可晚於原結束時間）")

            # 查詢課程時長
            course_result = await supabase_service.table_select(
                table="courses",
                select="duration_minutes",
                filters={"id": existing[0]["course_id"], "is_deleted": "eq.false"},
            )
            course_duration = course_result[0].get("duration_minutes", 60) if course_result else 60

            new_booking_minutes = (data.end_time.hour * 60 + data.end_time.minute) - (orig_start.hour * 60 + orig_start.minute)
            if new_booking_minutes % course_duration != 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"縮短後時長 ({new_booking_minutes}分鐘) 必須是課程時長 ({course_duration}分鐘) 的倍數"
                )

            old_lessons_used = existing[0].get("lessons_used", 1)
            new_lessons_used = calculate_lessons_used(orig_start, data.end_time, course_duration)
            end_time_delta = old_lessons_used - new_lessons_used  # 要退回的堂數

        # 更新預約
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}

        # 處理枚舉值
        if "booking_status" in update_data:
            update_data["booking_status"] = update_data["booking_status"].value

        # 處理 end_time 變更：同步更新 lessons_used
        if "end_time" in update_data:
            update_data["end_time"] = data.end_time.isoformat()
            update_data["lessons_used"] = new_lessons_used

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="bookings",
            data=update_data,
            filters={"id": booking_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新預約失敗")

        # 縮短預約：退回差額堂數到合約
        if end_time_delta > 0 and existing[0].get("student_contract_id"):
            contract = await supabase_service.table_select(
                table="student_contracts",
                select="remaining_lessons",
                filters={"id": existing[0]["student_contract_id"]},
            )
            if contract:
                await supabase_service.table_update(
                    table="student_contracts",
                    data={"remaining_lessons": contract[0]["remaining_lessons"] + end_time_delta},
                    filters={"id": existing[0]["student_contract_id"]},
                )

        # Zoom 整合：狀態變更時觸發
        new_status = update_data.get("booking_status")
        if new_status and new_status != old_status:
            try:
                from app.services.zoom_service import zoom_service
                from app.config import settings as app_settings
                if app_settings.zoom_enabled:
                    if new_status == "confirmed":
                        # 確認 → 建立 Zoom 會議
                        booking_date_val = existing[0].get("booking_date") or result.get("booking_date")
                        start_time_val = existing[0].get("start_time") or result.get("start_time")
                        end_time_val = existing[0].get("end_time") or result.get("end_time")
                        teacher_id_val = existing[0].get("teacher_id")
                        if booking_date_val and start_time_val and end_time_val and teacher_id_val:
                            if isinstance(booking_date_val, str):
                                booking_date_val = date.fromisoformat(booking_date_val)
                            if isinstance(start_time_val, str):
                                start_time_val = time.fromisoformat(start_time_val)
                            if isinstance(end_time_val, str):
                                end_time_val = time.fromisoformat(end_time_val)
                            asyncio.create_task(
                                zoom_service.create_meeting_for_booking(
                                    booking_id=booking_id,
                                    teacher_id=teacher_id_val,
                                    booking_date=booking_date_val,
                                    start_time_val=start_time_val,
                                    end_time_val=end_time_val,
                                )
                            )
                    elif new_status in ("cancelled", "pending"):
                        # 取消或退回待確認 → 刪除已存在的 Zoom 會議
                        asyncio.create_task(
                            zoom_service.cancel_meeting_for_booking(booking_id)
                        )
            except Exception as zoom_err:
                logging.getLogger(__name__).warning(f"Zoom 會議狀態變更觸發失敗: {zoom_err}")

        # 試上課完成：自動寫入「試上完成」獎金紀錄
        if new_status == "completed" and old_status != "completed":
            if existing[0].get("booking_type") == "trial":
                try:
                    teacher_id_val = existing[0].get("teacher_id")
                    tc_id = existing[0].get("teacher_contract_id")
                    # 從教師合約取得試上完成獎金金額
                    bonus_amount = 0
                    if tc_id:
                        tc_rows = await supabase_service.table_select(
                            table="teacher_contracts",
                            select="trial_completed_bonus",
                            filters={"id": tc_id, "is_deleted": "eq.false"},
                        )
                        if tc_rows:
                            bonus_amount = float(tc_rows[0].get("trial_completed_bonus", 0) or 0)
                    else:
                        # 未指定合約時，找教師的 active 合約
                        tc_rows = await supabase_service.table_select(
                            table="teacher_contracts",
                            select="trial_completed_bonus",
                            filters={
                                "teacher_id": teacher_id_val,
                                "contract_status": "eq.active",
                                "is_deleted": "eq.false",
                            },
                        )
                        if tc_rows:
                            bonus_amount = float(tc_rows[0].get("trial_completed_bonus", 0) or 0)

                    employee_id_val = await get_user_employee_id(current_user.user_id)
                    # 查學生名稱
                    student_name = ""
                    student_rows = await supabase_service.table_select(
                        table="students", select="name",
                        filters={"id": existing[0].get("student_id")},
                    )
                    if student_rows:
                        student_name = student_rows[0].get("name", "")

                    bonus_data = {
                        "teacher_id": teacher_id_val,
                        "bonus_type": "trial_completed",
                        "amount": bonus_amount,
                        "bonus_date": date.today().isoformat(),
                        "description": f"學生 {student_name} 試上完成獎金",
                        "related_student_id": existing[0].get("student_id"),
                        "related_booking_id": booking_id,
                    }
                    if employee_id_val:
                        bonus_data["created_by"] = employee_id_val
                    await supabase_service.table_insert(
                        table="teacher_bonus_records", data=bonus_data,
                    )
                    logging.getLogger(__name__).info(f"Booking {booking_id}: 試上完成獎金已記錄 (金額={bonus_amount})")
                except Exception as trial_bonus_err:
                    logging.getLogger(__name__).warning(f"Booking {booking_id}: 試上完成獎金記錄失敗: {trial_bonus_err}")

        # 如果狀態變更為取消，觸發取消副作用
        if new_status == "cancelled" and old_status != "cancelled":
            await cancel_booking_side_effects(existing[0])

        # 添加關聯名稱
        enriched = await enrich_booking_with_relations(result)

        return DataResponse(
            message="預約更新成功",
            data=BookingResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新預約失敗: {str(e)}")


@router.delete("/batch", response_model=BaseResponse)
async def batch_delete_bookings(
    data: BookingBatchDelete,
    current_user: CurrentUser = Depends(require_page_permission("bookings.delete"))
):
    """批次刪除預約（週期性篩選，僅限員工）"""
    try:
        # 查詢符合條件的預約
        filters = {"is_deleted": "eq.false"}

        if data.student_id:
            filters["student_id"] = f"eq.{data.student_id}"
        if data.teacher_id:
            filters["teacher_id"] = f"eq.{data.teacher_id}"
        if data.course_id:
            filters["course_id"] = f"eq.{data.course_id}"
        if data.filter_status:
            filters["booking_status"] = f"eq.{data.filter_status.value}"

        all_bookings = await supabase_service.table_select(
            table="bookings",
            select="id,booking_date,booking_status,teacher_slot_id,student_contract_id,lessons_used",
            filters=filters,
        )

        # 在 Python 中進行更精細的過濾
        bookings_to_delete = []
        skipped_confirmed = 0
        for booking in all_bookings:
            booking_date_str = booking.get("booking_date", "")
            booking_date_obj = date.fromisoformat(booking_date_str) if booking_date_str else None

            if not booking_date_obj:
                continue

            # 檢查日期範圍
            if booking_date_obj < data.start_date or booking_date_obj > data.end_date:
                continue

            # 檢查星期幾
            if data.weekdays is not None and booking_date_obj.weekday() not in data.weekdays:
                continue

            # 只有待確認或已取消的預約才可刪除
            if booking.get("booking_status") not in ("pending", "cancelled"):
                skipped_confirmed += 1
                continue

            bookings_to_delete.append(booking)

        if not bookings_to_delete:
            msg = "沒有符合條件的預約可刪除"
            if skipped_confirmed:
                msg += f"（{skipped_confirmed} 筆不可刪除的預約已跳過）"
            return BaseResponse(message=msg)

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        # 批次刪除
        deleted_count = 0
        restored_contracts = []
        affected_slot_ids = set()
        delete_time = datetime.utcnow().isoformat()
        delete_data_base = {
            "is_deleted": True,
            "deleted_at": delete_time,
        }
        if employee_id:
            delete_data_base["deleted_by"] = employee_id

        for booking in bookings_to_delete:
            old_status = booking.get("booking_status")

            # 軟刪除
            result = await supabase_service.table_update(
                table="bookings",
                data=delete_data_base,
                filters={"id": booking["id"]},
            )

            if result:
                deleted_count += 1

                if booking.get("teacher_slot_id"):
                    affected_slot_ids.add(booking["teacher_slot_id"])

                # 取消 Zoom 會議
                try:
                    from app.services.zoom_service import zoom_service
                    from app.config import settings as app_settings
                    if app_settings.zoom_enabled:
                        asyncio.create_task(
                            zoom_service.cancel_meeting_for_booking(booking["id"])
                        )
                except Exception:
                    pass

                # 如果預約尚未取消或完成，恢復堂數
                if old_status not in ["cancelled", "completed"]:
                    booking_lessons = booking.get("lessons_used", 1)
                    # 恢復學生合約剩餘堂數
                    contract = await supabase_service.table_select(
                        table="student_contracts",
                        select="remaining_lessons",
                        filters={"id": booking["student_contract_id"]},
                    )
                    if contract:
                        await supabase_service.table_update(
                            table="student_contracts",
                            data={"remaining_lessons": contract[0]["remaining_lessons"] + booking_lessons},
                            filters={"id": booking["student_contract_id"]},
                        )
                        restored_contracts.append(booking["student_contract_id"])

        # 更新所有受影響 slot 的預約已滿狀態
        for sid in affected_slot_ids:
            await update_slot_booked_status(sid)

        message = f"已刪除 {deleted_count} 筆預約"
        if skipped_confirmed:
            message += f"，跳過 {skipped_confirmed} 筆不可刪除的預約"
        if restored_contracts:
            message += f"，恢復 {len(restored_contracts)} 份合約堂數"
        return BaseResponse(message=message)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次刪除預約失敗: {str(e)}")


@router.delete("/{booking_id}", response_model=BaseResponse)
async def delete_booking(
    booking_id: str,
    current_user: CurrentUser = Depends(require_page_permission("bookings.delete"))
):
    """刪除預約（軟刪除，僅限員工）"""
    try:
        # 檢查預約是否存在
        existing = await supabase_service.table_select(
            table="bookings",
            select="id,booking_status,teacher_slot_id,student_contract_id,lessons_used",
            filters={"id": booking_id, "is_deleted": "eq.false"},
        )

        if not existing:
            raise HTTPException(status_code=404, detail="預約不存在")

        old_status = existing[0].get("booking_status")

        # 只有待確認或已取消的預約才可刪除
        if old_status not in ("pending", "cancelled"):
            raise HTTPException(status_code=400, detail="只有待確認或已取消狀態的預約才可刪除")

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        # 軟刪除
        delete_data = {
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        result = await supabase_service.table_update(
            table="bookings",
            data=delete_data,
            filters={"id": booking_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="刪除預約失敗")

        # 如果預約尚未取消或完成，恢復堂數
        if old_status not in ["cancelled", "completed"]:
            booking_lessons = existing[0].get("lessons_used", 1)
            # 恢復學生合約剩餘堂數
            contract = await supabase_service.table_select(
                table="student_contracts",
                select="remaining_lessons",
                filters={"id": existing[0]["student_contract_id"]},
            )
            if contract:
                await supabase_service.table_update(
                    table="student_contracts",
                    data={"remaining_lessons": contract[0]["remaining_lessons"] + booking_lessons},
                    filters={"id": existing[0]["student_contract_id"]},
                )

        # 更新 slot 預約已滿狀態
        if existing[0].get("teacher_slot_id"):
            await update_slot_booked_status(existing[0]["teacher_slot_id"])

        # 取消 Zoom 會議
        try:
            from app.services.zoom_service import zoom_service
            from app.config import settings as app_settings
            if app_settings.zoom_enabled:
                asyncio.create_task(
                    zoom_service.cancel_meeting_for_booking(booking_id)
                )
        except Exception:
            pass

        return BaseResponse(message="預約刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除預約失敗: {str(e)}")


# ============================================
# 批次操作 API
# ============================================

@router.post("/batch", response_model=BaseResponse)
async def batch_create_bookings(
    data: BookingBatchCreate,
    current_user: CurrentUser = Depends(require_page_permission("bookings.create"))
):
    """批次建立預約（週期性，自動匹配可用時段）"""
    try:
        # 權限檢查
        if current_user.is_student():
            # 學生只能為自己預約
            if not current_user.student_id:
                raise HTTPException(status_code=403, detail="無法取得學生資料")
            if data.student_id != current_user.student_id:
                raise HTTPException(status_code=403, detail="學生只能為自己預約")
        elif not current_user.is_staff():
            raise HTTPException(status_code=403, detail="無權建立預約")

        # 驗證學生存在
        student = await supabase_service.table_select(
            table="students",
            select="id,name,student_type",
            filters={"id": data.student_id, "is_deleted": "eq.false"},
        )
        if not student:
            raise HTTPException(status_code=400, detail="學生不存在")

        is_trial = student[0].get("student_type") == "trial"

        # 驗證教師存在
        teacher = await supabase_service.table_select(
            table="teachers",
            select="id,name,teacher_level",
            filters={"id": data.teacher_id, "is_deleted": "eq.false"},
        )
        if not teacher:
            raise HTTPException(status_code=400, detail="教師不存在")

        # 課程 ID：優先使用前端傳入的 course_id
        course_id = data.course_id
        if not course_id:
            raise HTTPException(status_code=400, detail="請提供課程 ID")

        # 查詢課程取得 duration_minutes
        batch_course = await supabase_service.table_select(
            table="courses",
            select="id,duration_minutes",
            filters={"id": course_id, "is_deleted": "eq.false"},
        )
        if not batch_course:
            raise HTTPException(status_code=400, detail="課程不存在")
        batch_course_duration = batch_course[0].get("duration_minutes", 60)

        # 驗證學生合約存在且有效（試上學生可不提供合約）
        student_contract = None
        remaining_lessons = None

        if data.student_contract_id:
            student_contract = await supabase_service.table_select(
                table="student_contracts",
                select="id,contract_no,remaining_lessons",
                filters={"id": data.student_contract_id, "is_deleted": "eq.false"},
            )
            if not student_contract:
                raise HTTPException(status_code=400, detail="學生合約不存在")

            remaining_lessons = student_contract[0].get("remaining_lessons", 0)
        elif not is_trial:
            raise HTTPException(status_code=400, detail="正式學生必須提供學生合約")

        # 驗證課程交集合法性：學生選課 ∩ 教師可教課程
        if course_id:
            # (a) 非 trial 學生：驗證 student_courses 有此 course_id
            if not is_trial:
                sc_check = await supabase_service.table_select(
                    table="student_courses",
                    select="id",
                    filters={
                        "student_id": data.student_id,
                        "course_id": course_id,
                        "is_deleted": "eq.false"
                    },
                )
                if not sc_check:
                    raise HTTPException(status_code=400, detail="學生未選修此課程")

            # (b) 所有情況：驗證老師有此課程的 course_rate
            batch_teacher_contracts = await supabase_service.table_select(
                table="teacher_contracts",
                select="id",
                filters={
                    "teacher_id": data.teacher_id,
                    "is_deleted": "eq.false",
                    "contract_status": "eq.active"
                },
            )
            has_course_rate = False
            for tc in batch_teacher_contracts:
                rate_check = await supabase_service.table_select(
                    table="teacher_contract_details",
                    select="id",
                    filters={
                        "teacher_contract_id": tc["id"],
                        "course_id": course_id,
                        "detail_type": "eq.course_rate",
                        "is_deleted": "eq.false"
                    },
                )
                if rate_check:
                    has_course_rate = True
                    break
            if not has_course_rate:
                raise HTTPException(status_code=400, detail="教師無此課程的授課資格")

        # 驗證教師等級是否符合學生偏好（主要教師不受等級限制）
        pref_list = await supabase_service.table_select(
            table="student_teacher_preferences",
            select="id,primary_teacher_id,min_teacher_level",
            filters={
                "student_id": data.student_id,
                "course_id": f"eq.{course_id}",
                "is_deleted": "eq.false"
            },
        )
        pref = pref_list[0] if pref_list else None
        if pref:
            is_primary = pref.get("primary_teacher_id") == data.teacher_id
            if not is_primary:
                teacher_level = teacher[0].get("teacher_level", 1)
                max_level = pref.get("min_teacher_level", 1)
                if teacher_level > max_level:
                    raise HTTPException(
                        status_code=400,
                        detail=f"教師等級 ({teacher_level}) 超過學生偏好的最高等級 ({max_level})"
                    )

        # 驗證教師合約存在（如果有提供）
        teacher_contract_id = data.teacher_contract_id
        if teacher_contract_id:
            teacher_contract = await supabase_service.table_select(
                table="teacher_contracts",
                select="id,contract_no",
                filters={"id": teacher_contract_id, "is_deleted": "eq.false"},
            )
            if not teacher_contract:
                raise HTTPException(status_code=400, detail="教師合約不存在")

        # 查詢教師在指定日期範圍內的可用時段（不再過濾 is_booked）
        slot_filters = {
            "teacher_id": f"eq.{data.teacher_id}",
            "is_deleted": "eq.false",
            "is_available": "eq.true",
        }

        all_slots = await supabase_service.table_select(
            table="teacher_available_slots",
            select="id,slot_date,start_time,end_time,teacher_contract_id",
            filters=slot_filters,
        )

        # 篩選符合條件的時段
        matching_slots = []
        for slot in all_slots:
            slot_date_str = slot.get("slot_date", "")
            slot_date_obj = date.fromisoformat(slot_date_str) if slot_date_str else None

            if not slot_date_obj:
                continue

            # 檢查日期範圍
            if slot_date_obj < data.start_date or slot_date_obj > data.end_date:
                continue

            # 檢查星期幾
            if slot_date_obj.weekday() not in data.weekdays:
                continue

            # 檢查時間範圍（如果有指定）— slot 時段必須包含請求的時間範圍
            slot_start = slot.get("start_time", "")[:5]
            slot_end = slot.get("end_time", "")[:5]

            if data.start_time is not None:
                if slot_start and slot_start > data.start_time.isoformat()[:5]:
                    continue

            if data.end_time is not None:
                if slot_end and slot_end < data.end_time.isoformat()[:5]:
                    continue

            # 檢查時間是否有重疊（使用請求的時間範圍，若未指定則用 slot 完整時間）
            booking_start = data.start_time.isoformat()[:5] if data.start_time else slot_start
            booking_end = data.end_time.isoformat()[:5] if data.end_time else slot_end
            overlapping = await check_booking_overlap(slot["id"], booking_start, booking_end)
            if not overlapping:
                matching_slots.append(slot)

        if not matching_slots:
            return BaseResponse(success=False, message="沒有符合條件的可用時段")

        # 計算每筆預約的 lessons_used 及總堂數需求
        total_lessons_needed = 0
        for slot in matching_slots:
            slot_start_str = data.start_time.isoformat()[:5] if data.start_time else slot.get("start_time", "")[:5]
            slot_end_str = data.end_time.isoformat()[:5] if data.end_time else slot.get("end_time", "")[:5]
            s_t = time.fromisoformat(slot_start_str)
            e_t = time.fromisoformat(slot_end_str)
            total_lessons_needed += calculate_lessons_used(s_t, e_t, batch_course_duration)

        # 檢查剩餘堂數是否足夠（試上學生無合約則跳過）
        if remaining_lessons is not None and remaining_lessons < total_lessons_needed:
            return BaseResponse(
                success=False,
                message=f"學生合約剩餘堂數不足（剩餘 {remaining_lessons} 堂，需要 {total_lessons_needed} 堂）"
            )

        # 取得教師時薪（從 teacher_contract_details）
        hourly_rate = 0
        rate_percentage = None
        if teacher_contract_id:
            teacher_rate = await supabase_service.table_select(
                table="teacher_contract_details",
                select="amount",
                filters={
                    "teacher_contract_id": teacher_contract_id,
                    "course_id": course_id,
                    "detail_type": "eq.course_rate",
                    "is_deleted": "eq.false"
                },
            )
            if teacher_rate:
                hourly_rate = teacher_rate[0].get("amount", 0)

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        # 批次建立預約
        created_count = 0
        failed_count = 0
        total_lessons_deducted = 0

        for slot in matching_slots:
            try:
                # 生成預約編號
                booking_no = await generate_booking_no()

                # 使用時段的教師合約（如果有）
                slot_teacher_contract_id = teacher_contract_id or slot.get("teacher_contract_id")

                # 計算此筆預約的 lessons_used
                slot_start_str = data.start_time.isoformat()[:5] if data.start_time else slot.get("start_time", "")[:5]
                slot_end_str = data.end_time.isoformat()[:5] if data.end_time else slot.get("end_time", "")[:5]
                s_t = time.fromisoformat(slot_start_str)
                e_t = time.fromisoformat(slot_end_str)
                slot_lessons_used = calculate_lessons_used(s_t, e_t, batch_course_duration)

                # 計算加班費
                slot_booking_date = date.fromisoformat(slot["slot_date"]) if isinstance(slot["slot_date"], str) else slot["slot_date"]
                batch_overtime_pay = None
                if slot_teacher_contract_id and not is_trial:
                    batch_overtime_pay = await compute_overtime_pay(
                        slot_teacher_contract_id, slot_booking_date,
                        s_t, e_t, batch_course_duration,
                    )

                # 建立預約
                booking_data = {
                    "booking_no": booking_no,
                    "student_id": data.student_id,
                    "teacher_id": data.teacher_id,
                    "course_id": course_id,
                    "student_contract_id": data.student_contract_id,
                    "teacher_contract_id": slot_teacher_contract_id,
                    "teacher_slot_id": slot["id"],
                    "teacher_hourly_rate": hourly_rate,
                    "teacher_rate_percentage": rate_percentage,
                    "booking_status": "pending",
                    "booking_date": slot["slot_date"],
                    "start_time": data.start_time.isoformat() if data.start_time else slot["start_time"],
                    "end_time": data.end_time.isoformat() if data.end_time else slot["end_time"],
                    "booking_type": "trial" if is_trial else "regular",
                    "lessons_used": slot_lessons_used,
                    "overtime_pay": batch_overtime_pay,
                    "notes": data.notes,
                }
                if employee_id:
                    booking_data["created_by"] = employee_id

                result = await supabase_service.table_insert(
                    table="bookings",
                    data=booking_data,
                )

                if result:
                    created_count += 1
                    total_lessons_deducted += slot_lessons_used
                else:
                    failed_count += 1

            except Exception:
                failed_count += 1

        # 扣除學生合約剩餘堂數（試上學生無合約則跳過）
        if total_lessons_deducted > 0 and student_contract and data.student_contract_id:
            new_remaining = remaining_lessons - total_lessons_deducted
            await supabase_service.table_update(
                table="student_contracts",
                data={"remaining_lessons": new_remaining},
                filters={"id": data.student_contract_id},
            )

        # 更新所有受影響 slot 的預約已滿狀態
        affected_slot_ids = set(slot["id"] for slot in matching_slots)
        for sid in affected_slot_ids:
            await update_slot_booked_status(sid)

        message = f"成功建立 {created_count} 筆預約"
        if failed_count > 0:
            message += f"，失敗 {failed_count} 筆"

        return BaseResponse(message=message)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次建立預約失敗: {str(e)}")


@router.post("/batch-by-ids/update", response_model=BaseResponse)
async def batch_update_bookings_by_ids(
    data: BookingBatchUpdateByIds,
    current_user: CurrentUser = Depends(require_page_permission("bookings.edit"))
):
    """根據 ID 批次更新預約狀態（僅限員工）"""
    try:
        if not data.booking_ids:
            raise HTTPException(status_code=400, detail="請提供預約 ID")

        updated_count = 0
        restored_contracts = []
        affected_slot_ids = set()

        for booking_id in data.booking_ids:
            # 檢查預約是否存在
            existing = await supabase_service.table_select(
                table="bookings",
                select="id,booking_status,teacher_slot_id,student_contract_id,lessons_used",
                filters={"id": booking_id, "is_deleted": "eq.false"},
            )

            if not existing:
                continue

            old_status = existing[0].get("booking_status")

            # 已取消的預約不可修改
            if old_status == "cancelled":
                continue

            # 準備更新資料
            update_data = {"booking_status": data.booking_status.value}
            if data.notes is not None:
                update_data["notes"] = data.notes

            # 更新預約
            result = await supabase_service.table_update(
                table="bookings",
                data=update_data,
                filters={"id": booking_id},
            )

            if result:
                updated_count += 1

                # 如果狀態變更為取消，恢復堂數
                if data.booking_status.value == "cancelled" and old_status != "cancelled":
                    booking_lessons = existing[0].get("lessons_used", 1)
                    # 恢復學生合約剩餘堂數
                    contract = await supabase_service.table_select(
                        table="student_contracts",
                        select="remaining_lessons",
                        filters={"id": existing[0]["student_contract_id"]},
                    )
                    if contract:
                        await supabase_service.table_update(
                            table="student_contracts",
                            data={"remaining_lessons": contract[0]["remaining_lessons"] + booking_lessons},
                            filters={"id": existing[0]["student_contract_id"]},
                        )
                        restored_contracts.append(existing[0]["student_contract_id"])

                    if existing[0].get("teacher_slot_id"):
                        affected_slot_ids.add(existing[0]["teacher_slot_id"])

        # 更新所有受影響 slot 的預約已滿狀態
        for sid in affected_slot_ids:
            await update_slot_booked_status(sid)

        message = f"已更新 {updated_count} 筆預約"
        if restored_contracts:
            message += f"，恢復 {len(restored_contracts)} 份合約堂數"

        return BaseResponse(message=message)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次更新預約失敗: {str(e)}")


@router.post("/batch-by-ids/delete", response_model=BaseResponse)
async def batch_delete_bookings_by_ids(
    data: BookingBatchDeleteByIds,
    current_user: CurrentUser = Depends(require_page_permission("bookings.delete"))
):
    """根據 ID 批次刪除預約（僅限員工）"""
    try:
        if not data.booking_ids:
            raise HTTPException(status_code=400, detail="請提供預約 ID")

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        deleted_count = 0
        skipped_confirmed = 0
        restored_contracts = []
        affected_slot_ids = set()
        delete_time = datetime.utcnow().isoformat()

        for booking_id in data.booking_ids:
            # 檢查預約是否存在
            existing = await supabase_service.table_select(
                table="bookings",
                select="id,booking_status,teacher_slot_id,student_contract_id,lessons_used",
                filters={"id": booking_id, "is_deleted": "eq.false"},
            )

            if not existing:
                continue

            old_status = existing[0].get("booking_status")

            # 只有待確認或已取消的預約才可刪除
            if old_status not in ("pending", "cancelled"):
                skipped_confirmed += 1
                continue

            # 軟刪除
            delete_data = {
                "is_deleted": True,
                "deleted_at": delete_time,
            }
            if employee_id:
                delete_data["deleted_by"] = employee_id

            result = await supabase_service.table_update(
                table="bookings",
                data=delete_data,
                filters={"id": booking_id},
            )

            if result:
                deleted_count += 1

                if existing[0].get("teacher_slot_id"):
                    affected_slot_ids.add(existing[0]["teacher_slot_id"])

                # 取消 Zoom 會議
                try:
                    from app.services.zoom_service import zoom_service
                    from app.config import settings as app_settings
                    if app_settings.zoom_enabled:
                        asyncio.create_task(
                            zoom_service.cancel_meeting_for_booking(booking_id)
                        )
                except Exception:
                    pass

                # 如果預約尚未取消或完成，恢復堂數
                if old_status not in ["cancelled", "completed"]:
                    booking_lessons = existing[0].get("lessons_used", 1)
                    # 恢復學生合約剩餘堂數
                    contract = await supabase_service.table_select(
                        table="student_contracts",
                        select="remaining_lessons",
                        filters={"id": existing[0]["student_contract_id"]},
                    )
                    if contract:
                        await supabase_service.table_update(
                            table="student_contracts",
                            data={"remaining_lessons": contract[0]["remaining_lessons"] + booking_lessons},
                            filters={"id": existing[0]["student_contract_id"]},
                        )
                        restored_contracts.append(existing[0]["student_contract_id"])

        # 更新所有受影響 slot 的預約已滿狀態
        for sid in affected_slot_ids:
            await update_slot_booked_status(sid)

        message = f"已刪除 {deleted_count} 筆預約"
        if skipped_confirmed:
            message += f"，跳過 {skipped_confirmed} 筆不可刪除的預約"
        if restored_contracts:
            message += f"，恢復 {len(restored_contracts)} 份合約堂數"

        return BaseResponse(message=message)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批次刪除預約失敗: {str(e)}")


# ============================================
# 輔助 API：取得下拉選單資料
# ============================================

@router.get("/options/students", tags=["預約管理"])
async def get_student_options(
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得學生下拉選單"""
    try:
        students = await supabase_service.table_select(
            table="students",
            select="id,student_no,name,student_type",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        return {"data": students}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/teachers", tags=["預約管理"])
async def get_teacher_options(
    student_id: Optional[str] = Query(None, description="學生 ID（用於偏好過濾）"),
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得教師下拉選單（可依學生偏好聯集過濾）"""
    try:
        filters: dict = {"is_deleted": "eq.false", "is_active": "eq.true"}

        if student_id:
            allowed_set, _ = await get_student_allowed_teachers(student_id)
            # 有傳 student_id → 一律依偏好白名單過濾（無偏好 = 空清單）
            teachers = await supabase_service.table_select(
                table="teachers",
                select="id,teacher_no,name,teacher_level",
                filters=filters,
            )
            teachers = [t for t in teachers if t["id"] in allowed_set]
        else:
            # 未傳 student_id → 回傳全部教師（用於篩選列表等）
            teachers = await supabase_service.table_select(
                table="teachers",
                select="id,teacher_no,name,teacher_level",
                filters=filters,
            )

        return {"data": teachers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/overlapping-courses", tags=["預約管理"])
async def get_overlapping_course_options(
    student_id: str = Query(..., description="學生 ID"),
    teacher_id: str = Query(..., description="教師 ID"),
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得學生與教師的交集課程（學生選課 ∩ 教師可教課程）

    - trial 學生：直接回傳老師的所有可教課程
    - 正式學生：回傳學生選課與老師可教課程的交集
    """
    try:
        # 1. 查學生類型
        student = await supabase_service.table_select(
            table="students",
            select="id,student_type",
            filters={"id": student_id, "is_deleted": "eq.false"},
        )
        if not student:
            raise HTTPException(status_code=400, detail="學生不存在")

        is_trial = student[0].get("student_type") == "trial"

        # 2. 查老師可教課程：teacher_contracts(active) → teacher_contract_details(course_rate)
        teacher_contracts = await supabase_service.table_select(
            table="teacher_contracts",
            select="id",
            filters={
                "teacher_id": teacher_id,
                "is_deleted": "eq.false",
                "contract_status": "eq.active"
            },
        )

        teacher_course_ids = set()
        for tc in teacher_contracts:
            details = await supabase_service.table_select(
                table="teacher_contract_details",
                select="course_id",
                filters={
                    "teacher_contract_id": tc["id"],
                    "detail_type": "eq.course_rate",
                    "is_deleted": "eq.false"
                },
            )
            for d in details:
                if d.get("course_id"):
                    teacher_course_ids.add(d["course_id"])

        if not teacher_course_ids:
            return {"data": []}

        # 3. 決定最終課程 IDs
        if is_trial:
            # trial 學生：直接用老師的課程
            final_course_ids = teacher_course_ids
        else:
            # 正式學生：查 student_courses 取交集
            student_courses = await supabase_service.table_select(
                table="student_courses",
                select="course_id",
                filters={
                    "student_id": student_id,
                    "is_deleted": "eq.false"
                },
            )
            student_course_ids = set(sc["course_id"] for sc in student_courses if sc.get("course_id"))

            final_course_ids = teacher_course_ids & student_course_ids

        if not final_course_ids:
            return {"data": []}

        # 4. 查課程資料
        courses = await supabase_service.table_select(
            table="courses",
            select="id,course_code,course_name",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )

        # 過濾交集課程
        result = [c for c in courses if c["id"] in final_course_ids]

        return {"data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/courses", tags=["預約管理"])
async def get_course_options(
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
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


@router.get("/options/student-contracts/{student_id}", tags=["預約管理"])
async def get_student_contract_options(
    student_id: str,
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得學生的合約下拉選單（按建立時間由新到舊排序）"""
    try:
        contracts = await supabase_service.table_select(
            table="student_contracts",
            select="id,contract_no,remaining_lessons,created_at",
            filters={
                "student_id": student_id,
                "is_deleted": "eq.false",
                "contract_status": "eq.active"
            },
        )

        # 按 created_at 降序排列（最新的在前）
        contracts.sort(key=lambda c: c.get("created_at", ""), reverse=True)

        # 從合約明細取得關聯課程
        enriched = []
        for contract in contracts:
            details = await supabase_service.table_select(
                table="student_contract_details",
                select="course_id",
                filters={
                    "student_contract_id": contract["id"],
                    "detail_type": "eq.lesson_price",
                    "is_deleted": "eq.false"
                },
            )
            course_ids = list(set(d["course_id"] for d in details if d.get("course_id")))
            course_names = []
            first_course_id = course_ids[0] if course_ids else None
            for cid in course_ids:
                c = await supabase_service.table_select(
                    table="courses",
                    select="course_name",
                    filters={"id": cid},
                )
                if c:
                    course_names.append(c[0]["course_name"])
            contract["course_id"] = first_course_id
            contract["course_ids"] = course_ids
            contract["course_name"] = ", ".join(course_names) if course_names else None
            enriched.append(contract)

        return {"data": enriched}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/substitute-teachers", tags=["預約管理"])
async def get_substitute_teacher_options(
    booking_id: str = Query(..., description="預約 ID"),
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得可用代課教師選項（依 slot / 課程 / 衝堂 三個硬條件篩選）"""
    try:
        # 1. 取得預約資料
        booking = await supabase_service.table_select(
            table="bookings",
            select="id,booking_date,start_time,end_time,course_id,teacher_id,student_id",
            filters={"id": booking_id, "is_deleted": "eq.false"},
        )
        if not booking:
            raise HTTPException(status_code=404, detail="預約不存在")
        b = booking[0]
        booking_date = b["booking_date"]
        booking_start = b.get("start_time", "")[:5]
        booking_end = b.get("end_time", "")[:5]
        course_id = b.get("course_id")
        original_teacher_id = b.get("teacher_id")
        student_id = b.get("student_id")

        # 2. 取得所有 active 教師（排除原教師）
        all_teachers = await supabase_service.table_select(
            table="teachers",
            select="id,teacher_no,name,teacher_level",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
        )
        candidates = [t for t in all_teachers if t["id"] != original_teacher_id]

        # 3. 取得學生偏好集合（僅用於標記 is_preferred）
        preferred_set: set[str] = set()
        if student_id:
            allowed_set, _ = await get_student_allowed_teachers(student_id)
            if allowed_set:
                preferred_set = allowed_set

        result = []
        for teacher in candidates:
            tid = teacher["id"]

            # 條件 a: 該日有涵蓋 booking 時段的 slot
            slots = await supabase_service.table_select(
                table="teacher_available_slots",
                select="id,start_time,end_time",
                filters={
                    "teacher_id": tid,
                    "slot_date": f"eq.{booking_date}",
                    "is_deleted": "eq.false",
                    "is_available": "eq.true",
                },
            )
            has_covering_slot = any(
                s.get("start_time", "")[:5] <= booking_start
                and s.get("end_time", "")[:5] >= booking_end
                for s in slots
            )
            if not has_covering_slot:
                continue

            # 條件 b: active 合約有該 course_id 的 course_rate
            if course_id:
                t_contracts = await supabase_service.table_select(
                    table="teacher_contracts",
                    select="id",
                    filters={
                        "teacher_id": tid,
                        "is_deleted": "eq.false",
                        "contract_status": "eq.active",
                    },
                )
                has_course = False
                for tc in t_contracts:
                    rate = await supabase_service.table_select(
                        table="teacher_contract_details",
                        select="id",
                        filters={
                            "teacher_contract_id": tc["id"],
                            "course_id": course_id,
                            "detail_type": "eq.course_rate",
                            "is_deleted": "eq.false",
                        },
                    )
                    if rate:
                        has_course = True
                        break
                if not has_course:
                    continue

            # 條件 c: 沒有衝堂（正式預約 + 代課安排）
            teacher_bookings = await supabase_service.table_select(
                table="bookings",
                select="id,start_time,end_time,booking_status",
                filters={
                    "teacher_id": f"eq.{tid}",
                    "booking_date": f"eq.{booking_date}",
                    "is_deleted": "eq.false",
                },
            )
            conflict = False
            for tb in teacher_bookings:
                if tb.get("booking_status") in ("cancelled",):
                    continue
                tb_start = tb.get("start_time", "")[:5]
                tb_end = tb.get("end_time", "")[:5]
                if booking_start < tb_end and booking_end > tb_start:
                    conflict = True
                    break

            if not conflict:
                # 也檢查作為代課者的安排
                existing_subs = await supabase_service.table_select(
                    table="substitute_details",
                    select="id,booking_id",
                    filters={
                        "substitute_teacher_id": f"eq.{tid}",
                        "is_deleted": "eq.false",
                    },
                )
                for sub in existing_subs:
                    sub_booking = await supabase_service.table_select(
                        table="bookings",
                        select="id,booking_date,start_time,end_time,booking_status",
                        filters={"id": sub["booking_id"], "is_deleted": "eq.false"},
                    )
                    if sub_booking:
                        sb = sub_booking[0]
                        if sb.get("booking_status") in ("cancelled",):
                            continue
                        if sb.get("booking_date") != booking_date:
                            continue
                        sb_start = sb.get("start_time", "")[:5]
                        sb_end = sb.get("end_time", "")[:5]
                        if booking_start < sb_end and booking_end > sb_start:
                            conflict = True
                            break

            if conflict:
                continue

            result.append({
                "id": tid,
                "teacher_no": teacher.get("teacher_no"),
                "name": teacher.get("name"),
                "teacher_level": teacher.get("teacher_level"),
                "is_preferred": tid in preferred_set,
            })

        # 排序：is_preferred=True 排前面
        result.sort(key=lambda x: (not x["is_preferred"], x.get("teacher_no", "")))
        return {"data": result}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/teacher-contracts/{teacher_id}", tags=["預約管理"])
async def get_teacher_contract_options(
    teacher_id: str,
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得教師的合約下拉選單"""
    try:
        contracts = await supabase_service.table_select(
            table="teacher_contracts",
            select="id,contract_no",
            filters={
                "teacher_id": teacher_id,
                "is_deleted": "eq.false",
                "contract_status": "eq.active"
            },
        )
        return {"data": contracts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/teacher-slots/{teacher_id}", tags=["預約管理"])
async def get_teacher_slot_options(
    teacher_id: str,
    date_from: Optional[date] = Query(None, description="開始日期"),
    date_to: Optional[date] = Query(None, description="結束日期"),
    current_user: CurrentUser = Depends(require_page_permission("bookings.list"))
):
    """取得教師的可用時段（不再過濾 is_booked，改由前端顯示區塊可用性）"""
    try:
        filters = {
            "teacher_id": teacher_id,
            "is_deleted": "eq.false",
            "is_available": "eq.true",
        }

        if date_from:
            filters["slot_date"] = f"gte.{date_from.isoformat()}"

        slots = await supabase_service.table_select(
            table="teacher_available_slots",
            select="id,slot_date,start_time,end_time,teacher_contract_id,is_booked",
            filters=filters,
        )

        # 如果有結束日期，在結果中篩選
        if date_to:
            slots = [s for s in slots if s.get("slot_date") <= date_to.isoformat()]

        return {"data": slots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


