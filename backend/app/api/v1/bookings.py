from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, get_user_employee_id
from app.schemas.booking import (
    BookingCreate, BookingUpdate, BookingResponse, BookingListResponse, BookingStatus,
    BookingBatchUpdateByIds, BookingBatchDeleteByIds, BookingBatchUpdate, BookingBatchDelete,
    BookingBatchCreate, TimeBlock, SlotAvailabilityResponse
)
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import date, datetime, time
import math

router = APIRouter(prefix="/bookings", tags=["預約管理"])


async def generate_booking_no() -> str:
    """生成預約編號: BK{YYYYMMDD}{序號}"""
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"BK{today}"

    # 查詢今天已有多少預約
    result = await supabase_service.table_select(
        table="bookings",
        select="booking_no",
        filters={"booking_no": f"like.{prefix}%"},
        use_service_key=True
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
    """取得學生所有偏好設定的教師聯集

    遍歷所有偏好（is_deleted=false），依情境收集可預約教師 ID：
      情境 1: primary_teacher_id 有值 → 直接加入該教師
      情境 2: course_id=NULL + min_teacher_level → 全域等級過濾
      情境 3: course_id=X  + min_teacher_level → 指定課程等級過濾

    Returns:
        (allowed_set, has_preferences)
        - allowed_set: 可預約教師 ID set；若無偏好設定則為 None
        - has_preferences: 是否有任何偏好設定
    """
    all_prefs = await supabase_service.table_select(
        table="student_teacher_preferences",
        select="id,min_teacher_level,primary_teacher_id,course_id",
        filters={
            "student_id": student_id,
            "is_deleted": "eq.false"
        },
        use_service_key=True
    )

    if not all_prefs:
        # 沒有偏好設定 → 回傳空集合（不可預約任何教師）
        return set(), False

    allowed: set[str] = set()

    for pref in all_prefs:
        primary = pref.get("primary_teacher_id")
        min_level = pref.get("min_teacher_level") or 1
        pref_course_id = pref.get("course_id")

        if primary:
            # 情境 1: 指定主要教師 → 直接加入
            allowed.add(primary)
        elif pref_course_id:
            # 情境 3: 指定課程 + 等級過濾
            # 查有該課程 course_rate 的教師（透過 teacher_contracts → teacher_contract_details）
            # 先找等級足夠的教師
            teachers = await supabase_service.table_select(
                table="teachers",
                select="id",
                filters={
                    "is_deleted": "eq.false",
                    "is_active": "eq.true",
                    "teacher_level": f"gte.{min_level}"
                },
                use_service_key=True
            )
            for t in teachers:
                # 查該教師是否有 active 合約包含此課程的 course_rate
                t_contracts = await supabase_service.table_select(
                    table="teacher_contracts",
                    select="id",
                    filters={
                        "teacher_id": t["id"],
                        "is_deleted": "eq.false",
                        "contract_status": "eq.active"
                    },
                    use_service_key=True
                )
                for tc in t_contracts:
                    rate_check = await supabase_service.table_select(
                        table="teacher_contract_details",
                        select="id",
                        filters={
                            "teacher_contract_id": tc["id"],
                            "course_id": pref_course_id,
                            "detail_type": "eq.course_rate",
                            "is_deleted": "eq.false"
                        },
                        use_service_key=True
                    )
                    if rate_check:
                        allowed.add(t["id"])
                        break
        else:
            # 情境 2: 全域等級過濾（course_id=NULL, 無 primary）
            teachers = await supabase_service.table_select(
                table="teachers",
                select="id",
                filters={
                    "is_deleted": "eq.false",
                    "is_active": "eq.true",
                    "teacher_level": f"gte.{min_level}"
                },
                use_service_key=True
            )
            for t in teachers:
                allowed.add(t["id"])

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
        use_service_key=True
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
        use_service_key=True
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
        use_service_key=True
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
        use_service_key=True
    )


async def enrich_booking_with_relations(booking: dict) -> dict:
    """為預約資料添加關聯名稱"""
    # 取得學生名稱
    if booking.get("student_id"):
        student = await supabase_service.table_select(
            table="students",
            select="name",
            filters={"id": booking["student_id"]},
            use_service_key=True
        )
        booking["student_name"] = student[0]["name"] if student else None

    # 取得教師名稱
    if booking.get("teacher_id"):
        teacher = await supabase_service.table_select(
            table="teachers",
            select="name",
            filters={"id": booking["teacher_id"]},
            use_service_key=True
        )
        booking["teacher_name"] = teacher[0]["name"] if teacher else None

    # 取得課程名稱
    if booking.get("course_id"):
        course = await supabase_service.table_select(
            table="courses",
            select="course_name",
            filters={"id": booking["course_id"]},
            use_service_key=True
        )
        booking["course_name"] = course[0]["course_name"] if course else None

    # 取得學生合約編號
    if booking.get("student_contract_id"):
        contract = await supabase_service.table_select(
            table="student_contracts",
            select="contract_no",
            filters={"id": booking["student_contract_id"]},
            use_service_key=True
        )
        booking["student_contract_no"] = contract[0]["contract_no"] if contract else None

    # 取得教師合約編號
    if booking.get("teacher_contract_id"):
        contract = await supabase_service.table_select(
            table="teacher_contracts",
            select="contract_no",
            filters={"id": booking["teacher_contract_id"]},
            use_service_key=True
        )
        booking["teacher_contract_no"] = contract[0]["contract_no"] if contract else None

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
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得預約列表"""
    try:
        # 建立基本查詢
        filters = {"is_deleted": "eq.false"}

        if booking_status:
            filters["booking_status"] = f"eq.{booking_status.value}"

        if student_id:
            filters["student_id"] = f"eq.{student_id}"

        if teacher_id:
            filters["teacher_id"] = f"eq.{teacher_id}"

        if course_id:
            filters["course_id"] = f"eq.{course_id}"

        if date_from:
            filters["booking_date"] = f"gte.{date_from.isoformat()}"

        if date_to:
            if "booking_date" in filters:
                # 如果已有 date_from，需要用 and 邏輯
                pass  # PostgREST 限制，簡化處理
            else:
                filters["booking_date"] = f"lte.{date_to.isoformat()}"

        # 根據角色過濾（查詢資料庫取得關聯 ID）
        user_role = current_user.role

        if user_role == "student":
            user_student_id = await get_user_student_id(current_user.user_id)
            if user_student_id:
                filters["student_id"] = f"eq.{user_student_id}"
        elif user_role == "teacher":
            user_teacher_id = await get_user_teacher_id(current_user.user_id)
            if user_teacher_id:
                filters["teacher_id"] = f"eq.{user_teacher_id}"

        # 取得總數
        all_bookings = await supabase_service.table_select(
            table="bookings",
            select="id",
            filters=filters,
            use_service_key=True
        )
        total = len(all_bookings)

        # 計算分頁
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        # 取得分頁資料
        bookings = await supabase_service.table_select_with_pagination(
            table="bookings",
            select="id,booking_no,student_id,teacher_id,course_id,student_contract_id,teacher_contract_id,teacher_slot_id,teacher_hourly_rate,teacher_rate_percentage,booking_status,booking_date,start_time,end_time,notes,created_at,updated_at",
            filters=filters,
            order_by="booking_date.desc,start_time.desc",
            limit=per_page,
            offset=offset,
            use_service_key=True
        )

        # 如果有搜尋關鍵字，在結果中篩選
        if search:
            search_lower = search.lower()
            bookings = [
                b for b in bookings
                if search_lower in b.get("booking_no", "").lower()
            ]

        # 為每筆預約添加關聯名稱
        enriched_bookings = []
        for booking in bookings:
            enriched = await enrich_booking_with_relations(booking)
            enriched_bookings.append(enriched)

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
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得指定教師時段的 30 分鐘區塊可用狀態"""
    try:
        # 取得時段資料
        slot = await supabase_service.table_select(
            table="teacher_available_slots",
            select="id,slot_date,start_time,end_time,is_available",
            filters={"id": teacher_slot_id, "is_deleted": "eq.false"},
            use_service_key=True
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
            use_service_key=True
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
        user_student_id = await get_user_student_id(current_user.user_id)

        if not user_student_id:
            return {"data": None}

        student = await supabase_service.table_select(
            table="students",
            select="id,student_no,name,student_type",
            filters={"id": user_student_id, "is_deleted": "eq.false"},
            use_service_key=True
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
        user_student_id = await get_user_student_id(current_user.user_id)

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
            use_service_key=True
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
                use_service_key=True
            )
            course_ids = list(set(d["course_id"] for d in details if d.get("course_id")))
            course_names = []
            first_course_id = course_ids[0] if course_ids else None
            for cid in course_ids:
                c = await supabase_service.table_select(
                    table="courses",
                    select="course_name",
                    filters={"id": cid},
                    use_service_key=True
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
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得單一預約"""
    try:
        result = await supabase_service.table_select(
            table="bookings",
            select="id,booking_no,student_id,teacher_id,course_id,student_contract_id,teacher_contract_id,teacher_slot_id,teacher_hourly_rate,teacher_rate_percentage,booking_status,booking_date,start_time,end_time,notes,created_at,updated_at",
            filters={"id": booking_id, "is_deleted": "eq.false"},
            use_service_key=True
        )

        if not result:
            raise HTTPException(status_code=404, detail="預約不存在")

        booking = await enrich_booking_with_relations(result[0])
        return DataResponse(data=BookingResponse(**booking))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得預約失敗: {str(e)}")


async def get_user_student_id(user_id: str) -> str | None:
    """取得用戶關聯的學生 ID"""
    profile = await supabase_service.table_select(
        table="user_profiles",
        select="student_id",
        filters={"id": user_id},
        use_service_key=True
    )
    if profile and profile[0].get("student_id"):
        return profile[0]["student_id"]
    return None


async def get_user_teacher_id(user_id: str) -> str | None:
    """取得用戶關聯的教師 ID"""
    profile = await supabase_service.table_select(
        table="user_profiles",
        select="teacher_id",
        filters={"id": user_id},
        use_service_key=True
    )
    if profile and profile[0].get("teacher_id"):
        return profile[0]["teacher_id"]
    return None


@router.post("", response_model=DataResponse[BookingResponse])
async def create_booking(
    data: BookingCreate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """建立預約（員工可為任何學生預約，學生只能為自己預約）"""
    try:
        user_role = current_user.role

        # 權限檢查
        if user_role == "student":
            # 學生只能為自己預約
            user_student_id = await get_user_student_id(current_user.user_id)
            if not user_student_id:
                raise HTTPException(status_code=403, detail="無法取得學生資料")
            if data.student_id != user_student_id:
                raise HTTPException(status_code=403, detail="學生只能為自己預約")
        elif user_role not in ["admin", "employee"]:
            # 教師和其他角色不能建立預約
            raise HTTPException(status_code=403, detail="無權建立預約")

        # 驗證學生存在
        student = await supabase_service.table_select(
            table="students",
            select="id,name,student_type",
            filters={"id": data.student_id, "is_deleted": "eq.false"},
            use_service_key=True
        )
        if not student:
            raise HTTPException(status_code=400, detail="學生不存在")

        is_trial = student[0].get("student_type") == "trial"

        # 驗證教師存在
        teacher = await supabase_service.table_select(
            table="teachers",
            select="id,name,teacher_level",
            filters={"id": data.teacher_id, "is_deleted": "eq.false"},
            use_service_key=True
        )
        if not teacher:
            raise HTTPException(status_code=400, detail="教師不存在")

        # 驗證課程存在
        course = await supabase_service.table_select(
            table="courses",
            select="id,course_name",
            filters={"id": data.course_id, "is_deleted": "eq.false"},
            use_service_key=True
        )
        if not course:
            raise HTTPException(status_code=400, detail="課程不存在")

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
                use_service_key=True
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
            use_service_key=True
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
                use_service_key=True
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
                use_service_key=True
            )
            if not student_contract:
                raise HTTPException(status_code=400, detail="學生合約不存在")
            if student_contract[0].get("remaining_lessons", 0) <= 0:
                raise HTTPException(status_code=400, detail="學生合約剩餘堂數不足")
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
                use_service_key=True
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
                use_service_key=True
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
                use_service_key=True
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
                use_service_key=True
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

        # 生成預約編號
        booking_no = await generate_booking_no()

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        # 建立預約
        booking_data = {
            "booking_no": booking_no,
            "student_id": data.student_id,
            "teacher_id": data.teacher_id,
            "course_id": data.course_id,
            "student_contract_id": data.student_contract_id,
            "teacher_contract_id": teacher_contract_id,
            "teacher_slot_id": teacher_slot_id,
            "teacher_hourly_rate": hourly_rate,
            "teacher_rate_percentage": rate_percentage,
            "booking_status": "pending",
            "booking_date": data.booking_date.isoformat(),
            "start_time": data.start_time.isoformat(),
            "end_time": data.end_time.isoformat(),
            "notes": data.notes,
        }
        if employee_id:
            booking_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="bookings",
            data=booking_data,
            use_service_key=True
        )

        if not result:
            raise HTTPException(status_code=500, detail="建立預約失敗")

        # 扣除學生合約剩餘堂數（試上學生無合約則跳過）
        if student_contract and data.student_contract_id:
            await supabase_service.table_update(
                table="student_contracts",
                data={"remaining_lessons": student_contract[0]["remaining_lessons"] - 1},
                filters={"id": data.student_contract_id},
                use_service_key=True
            )

        # 更新 slot 預約已滿狀態
        await update_slot_booked_status(teacher_slot_id)

        # 添加關聯名稱
        enriched = await enrich_booking_with_relations(result)

        return DataResponse(
            message="預約建立成功",
            data=BookingResponse(**enriched)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立預約失敗: {str(e)}")


@router.put("/{booking_id}", response_model=DataResponse[BookingResponse])
async def update_booking(
    booking_id: str,
    data: BookingUpdate,
    current_user: CurrentUser = Depends(get_current_user)
):
    """更新預約（員工可完整更新，教師僅可將自己的預約確認）"""
    try:
        # 檢查預約是否存在
        existing = await supabase_service.table_select(
            table="bookings",
            select="id,booking_status,teacher_slot_id,student_contract_id,teacher_id",
            filters={"id": booking_id, "is_deleted": "eq.false"},
            use_service_key=True
        )

        if not existing:
            raise HTTPException(status_code=404, detail="預約不存在")

        old_status = existing[0].get("booking_status")

        # 教師權限：僅能將自己的預約狀態改為 confirmed
        if current_user.is_teacher():
            user_teacher_id = await get_user_teacher_id(current_user.user_id)
            if existing[0].get("teacher_id") != user_teacher_id:
                raise HTTPException(status_code=403, detail="教師只能更新自己的預約")
            if not data.booking_status or data.booking_status.value != "confirmed":
                raise HTTPException(status_code=403, detail="教師僅可將預約狀態更新為已確認")
            if old_status != "pending":
                raise HTTPException(status_code=400, detail="只有待確認的預約可以確認")
        elif current_user.is_student():
            raise HTTPException(status_code=403, detail="學生無權更新預約")

        # 已取消的預約不可修改
        if old_status == "cancelled":
            raise HTTPException(status_code=400, detail="已取消的預約無法修改")

        # 更新預約
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}

        # 處理枚舉值
        if "booking_status" in update_data:
            update_data["booking_status"] = update_data["booking_status"].value

        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="bookings",
            data=update_data,
            filters={"id": booking_id},
            use_service_key=True
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新預約失敗")

        # 如果狀態變更為取消，恢復堂數
        new_status = update_data.get("booking_status")
        if new_status == "cancelled" and old_status != "cancelled":
            # 恢復學生合約剩餘堂數
            contract = await supabase_service.table_select(
                table="student_contracts",
                select="remaining_lessons",
                filters={"id": existing[0]["student_contract_id"]},
                use_service_key=True
            )
            if contract:
                await supabase_service.table_update(
                    table="student_contracts",
                    data={"remaining_lessons": contract[0]["remaining_lessons"] + 1},
                    filters={"id": existing[0]["student_contract_id"]},
                    use_service_key=True
                )

            # 更新 slot 預約已滿狀態
            if existing[0].get("teacher_slot_id"):
                await update_slot_booked_status(existing[0]["teacher_slot_id"])

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


@router.delete("/{booking_id}", response_model=BaseResponse)
async def delete_booking(
    booking_id: str,
    current_user: CurrentUser = Depends(require_staff)
):
    """刪除預約（軟刪除，僅限員工）"""
    try:
        # 檢查預約是否存在
        existing = await supabase_service.table_select(
            table="bookings",
            select="id,booking_status,teacher_slot_id,student_contract_id",
            filters={"id": booking_id, "is_deleted": "eq.false"},
            use_service_key=True
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
            use_service_key=True
        )

        if not result:
            raise HTTPException(status_code=500, detail="刪除預約失敗")

        # 如果預約尚未取消或完成，恢復堂數
        if old_status not in ["cancelled", "completed"]:
            # 恢復學生合約剩餘堂數
            contract = await supabase_service.table_select(
                table="student_contracts",
                select="remaining_lessons",
                filters={"id": existing[0]["student_contract_id"]},
                use_service_key=True
            )
            if contract:
                await supabase_service.table_update(
                    table="student_contracts",
                    data={"remaining_lessons": contract[0]["remaining_lessons"] + 1},
                    filters={"id": existing[0]["student_contract_id"]},
                    use_service_key=True
                )

        # 更新 slot 預約已滿狀態
        if existing[0].get("teacher_slot_id"):
            await update_slot_booked_status(existing[0]["teacher_slot_id"])

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
    current_user: CurrentUser = Depends(get_current_user)
):
    """批次建立預約（週期性，自動匹配可用時段）"""
    try:
        user_role = current_user.role

        # 權限檢查
        if user_role == "student":
            # 學生只能為自己預約
            user_student_id = await get_user_student_id(current_user.user_id)
            if not user_student_id:
                raise HTTPException(status_code=403, detail="無法取得學生資料")
            if data.student_id != user_student_id:
                raise HTTPException(status_code=403, detail="學生只能為自己預約")
        elif user_role not in ["admin", "employee"]:
            raise HTTPException(status_code=403, detail="無權建立預約")

        # 驗證學生存在
        student = await supabase_service.table_select(
            table="students",
            select="id,name,student_type",
            filters={"id": data.student_id, "is_deleted": "eq.false"},
            use_service_key=True
        )
        if not student:
            raise HTTPException(status_code=400, detail="學生不存在")

        is_trial = student[0].get("student_type") == "trial"

        # 驗證教師存在
        teacher = await supabase_service.table_select(
            table="teachers",
            select="id,name,teacher_level",
            filters={"id": data.teacher_id, "is_deleted": "eq.false"},
            use_service_key=True
        )
        if not teacher:
            raise HTTPException(status_code=400, detail="教師不存在")

        # 課程 ID：優先使用前端傳入的 course_id
        course_id = data.course_id
        if not course_id:
            raise HTTPException(status_code=400, detail="請提供課程 ID")

        # 驗證學生合約存在且有效（試上學生可不提供合約）
        student_contract = None
        remaining_lessons = None

        if data.student_contract_id:
            student_contract = await supabase_service.table_select(
                table="student_contracts",
                select="id,contract_no,remaining_lessons",
                filters={"id": data.student_contract_id, "is_deleted": "eq.false"},
                use_service_key=True
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
                    use_service_key=True
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
                use_service_key=True
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
                    use_service_key=True
                )
                if rate_check:
                    has_course_rate = True
                    break
            if not has_course_rate:
                raise HTTPException(status_code=400, detail="教師無此課程的授課資格")

        # 驗證教師等級是否符合學生偏好（主要教師不受等級限制）
        pref = await get_student_teacher_preference(data.student_id, course_id)
        if pref:
            is_primary = pref.get("primary_teacher_id") == data.teacher_id
            if not is_primary:
                teacher_level = teacher[0].get("teacher_level", 1)
                min_level = pref.get("min_teacher_level", 1)
                if teacher_level < min_level:
                    raise HTTPException(
                        status_code=400,
                        detail=f"教師等級 ({teacher_level}) 低於學生要求的最低等級 ({min_level})"
                    )

        # 驗證教師合約存在（如果有提供）
        teacher_contract_id = data.teacher_contract_id
        if teacher_contract_id:
            teacher_contract = await supabase_service.table_select(
                table="teacher_contracts",
                select="id,contract_no",
                filters={"id": teacher_contract_id, "is_deleted": "eq.false"},
                use_service_key=True
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
            use_service_key=True
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

            # 檢查時間範圍（如果有指定）
            if data.start_time is not None:
                slot_start = slot.get("start_time", "")
                if slot_start and slot_start[:5] != data.start_time.isoformat()[:5]:
                    continue

            if data.end_time is not None:
                slot_end = slot.get("end_time", "")
                if slot_end and slot_end[:5] != data.end_time.isoformat()[:5]:
                    continue

            # 檢查時間是否有重疊（整個 slot 時間）
            slot_start_str = slot.get("start_time", "")[:5]
            slot_end_str = slot.get("end_time", "")[:5]
            overlapping = await check_booking_overlap(slot["id"], slot_start_str, slot_end_str)
            if not overlapping:
                matching_slots.append(slot)

        if not matching_slots:
            return BaseResponse(message="沒有符合條件的可用時段")

        # 檢查剩餘堂數是否足夠（試上學生無合約則跳過）
        if remaining_lessons is not None and remaining_lessons < len(matching_slots):
            return BaseResponse(
                success=False,
                message=f"學生合約剩餘堂數不足（剩餘 {remaining_lessons} 堂，需要 {len(matching_slots)} 堂）"
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
                use_service_key=True
            )
            if teacher_rate:
                hourly_rate = teacher_rate[0].get("amount", 0)

        # 取得操作者的 employee_id
        employee_id = await get_user_employee_id(current_user.user_id)

        # 批次建立預約
        created_count = 0
        failed_count = 0

        for slot in matching_slots:
            try:
                # 生成預約編號
                booking_no = await generate_booking_no()

                # 使用時段的教師合約（如果有）
                slot_teacher_contract_id = teacher_contract_id or slot.get("teacher_contract_id")

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
                    "start_time": slot["start_time"],
                    "end_time": slot["end_time"],
                    "notes": data.notes,
                }
                if employee_id:
                    booking_data["created_by"] = employee_id

                result = await supabase_service.table_insert(
                    table="bookings",
                    data=booking_data,
                    use_service_key=True
                )

                if result:
                    created_count += 1
                else:
                    failed_count += 1

            except Exception:
                failed_count += 1

        # 扣除學生合約剩餘堂數（試上學生無合約則跳過）
        if created_count > 0 and student_contract and data.student_contract_id:
            new_remaining = remaining_lessons - created_count
            await supabase_service.table_update(
                table="student_contracts",
                data={"remaining_lessons": new_remaining},
                filters={"id": data.student_contract_id},
                use_service_key=True
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
    current_user: CurrentUser = Depends(require_staff)
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
                select="id,booking_status,teacher_slot_id,student_contract_id",
                filters={"id": booking_id, "is_deleted": "eq.false"},
                use_service_key=True
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
                use_service_key=True
            )

            if result:
                updated_count += 1

                # 如果狀態變更為取消，恢復堂數
                if data.booking_status.value == "cancelled" and old_status != "cancelled":
                    # 恢復學生合約剩餘堂數
                    contract = await supabase_service.table_select(
                        table="student_contracts",
                        select="remaining_lessons",
                        filters={"id": existing[0]["student_contract_id"]},
                        use_service_key=True
                    )
                    if contract:
                        await supabase_service.table_update(
                            table="student_contracts",
                            data={"remaining_lessons": contract[0]["remaining_lessons"] + 1},
                            filters={"id": existing[0]["student_contract_id"]},
                            use_service_key=True
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
    current_user: CurrentUser = Depends(require_staff)
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
                select="id,booking_status,teacher_slot_id,student_contract_id",
                filters={"id": booking_id, "is_deleted": "eq.false"},
                use_service_key=True
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
                use_service_key=True
            )

            if result:
                deleted_count += 1

                if existing[0].get("teacher_slot_id"):
                    affected_slot_ids.add(existing[0]["teacher_slot_id"])

                # 如果預約尚未取消或完成，恢復堂數
                if old_status not in ["cancelled", "completed"]:
                    # 恢復學生合約剩餘堂數
                    contract = await supabase_service.table_select(
                        table="student_contracts",
                        select="remaining_lessons",
                        filters={"id": existing[0]["student_contract_id"]},
                        use_service_key=True
                    )
                    if contract:
                        await supabase_service.table_update(
                            table="student_contracts",
                            data={"remaining_lessons": contract[0]["remaining_lessons"] + 1},
                            filters={"id": existing[0]["student_contract_id"]},
                            use_service_key=True
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


@router.put("/batch", response_model=BaseResponse)
async def batch_update_bookings(
    data: BookingBatchUpdate,
    current_user: CurrentUser = Depends(require_staff)
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
            select="id,booking_date,booking_status,teacher_slot_id,student_contract_id",
            filters=filters,
            use_service_key=True
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
                use_service_key=True
            )

            if result:
                updated_count += 1

                # 如果狀態變更為取消，恢復堂數
                if data.new_status.value == "cancelled" and old_status != "cancelled":
                    # 恢復學生合約剩餘堂數
                    contract = await supabase_service.table_select(
                        table="student_contracts",
                        select="remaining_lessons",
                        filters={"id": booking["student_contract_id"]},
                        use_service_key=True
                    )
                    if contract:
                        await supabase_service.table_update(
                            table="student_contracts",
                            data={"remaining_lessons": contract[0]["remaining_lessons"] + 1},
                            filters={"id": booking["student_contract_id"]},
                            use_service_key=True
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


@router.delete("/batch", response_model=BaseResponse)
async def batch_delete_bookings(
    data: BookingBatchDelete,
    current_user: CurrentUser = Depends(require_staff)
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
            select="id,booking_date,booking_status,teacher_slot_id,student_contract_id",
            filters=filters,
            use_service_key=True
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
                use_service_key=True
            )

            if result:
                deleted_count += 1

                if booking.get("teacher_slot_id"):
                    affected_slot_ids.add(booking["teacher_slot_id"])

                # 如果預約尚未取消或完成，恢復堂數
                if old_status not in ["cancelled", "completed"]:
                    # 恢復學生合約剩餘堂數
                    contract = await supabase_service.table_select(
                        table="student_contracts",
                        select="remaining_lessons",
                        filters={"id": booking["student_contract_id"]},
                        use_service_key=True
                    )
                    if contract:
                        await supabase_service.table_update(
                            table="student_contracts",
                            data={"remaining_lessons": contract[0]["remaining_lessons"] + 1},
                            filters={"id": booking["student_contract_id"]},
                            use_service_key=True
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


# ============================================
# 輔助 API：取得下拉選單資料
# ============================================

@router.get("/options/students", tags=["預約管理"])
async def get_student_options(
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得學生下拉選單"""
    try:
        students = await supabase_service.table_select(
            table="students",
            select="id,student_no,name,student_type",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
            use_service_key=True
        )
        return {"data": students}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/teachers", tags=["預約管理"])
async def get_teacher_options(
    student_id: Optional[str] = Query(None, description="學生 ID（用於偏好過濾）"),
    current_user: CurrentUser = Depends(get_current_user)
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
                use_service_key=True
            )
            teachers = [t for t in teachers if t["id"] in allowed_set]
        else:
            # 未傳 student_id → 回傳全部教師（用於篩選列表等）
            teachers = await supabase_service.table_select(
                table="teachers",
                select="id,teacher_no,name,teacher_level",
                filters=filters,
                use_service_key=True
            )

        return {"data": teachers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/options/teachers/{teacher_id}/level", tags=["預約管理"])
async def update_teacher_level(
    teacher_id: str,
    level: int = Query(..., ge=1, description="教師等級"),
    current_user: CurrentUser = Depends(require_staff)
):
    """更新教師等級（僅員工）"""
    try:
        employee_id = await get_user_employee_id(current_user.user_id)

        teacher = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"id": teacher_id, "is_deleted": "eq.false"},
            use_service_key=True
        )
        if not teacher:
            raise HTTPException(status_code=404, detail="教師不存在")

        update_data = {"teacher_level": level}
        if employee_id:
            update_data["updated_by"] = employee_id

        result = await supabase_service.table_update(
            table="teachers",
            data=update_data,
            filters={"id": teacher_id},
            use_service_key=True
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新教師等級失敗")

        return {"success": True, "message": f"教師等級已更新為 {level}", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/overlapping-courses", tags=["預約管理"])
async def get_overlapping_course_options(
    student_id: str = Query(..., description="學生 ID"),
    teacher_id: str = Query(..., description="教師 ID"),
    current_user: CurrentUser = Depends(get_current_user)
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
            use_service_key=True
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
            use_service_key=True
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
                use_service_key=True
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
                use_service_key=True
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
            use_service_key=True
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
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得課程下拉選單"""
    try:
        courses = await supabase_service.table_select(
            table="courses",
            select="id,course_code,course_name",
            filters={"is_deleted": "eq.false", "is_active": "eq.true"},
            use_service_key=True
        )
        return {"data": courses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/student-contracts/{student_id}", tags=["預約管理"])
async def get_student_contract_options(
    student_id: str,
    current_user: CurrentUser = Depends(get_current_user)
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
            use_service_key=True
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
                use_service_key=True
            )
            course_ids = list(set(d["course_id"] for d in details if d.get("course_id")))
            course_names = []
            first_course_id = course_ids[0] if course_ids else None
            for cid in course_ids:
                c = await supabase_service.table_select(
                    table="courses",
                    select="course_name",
                    filters={"id": cid},
                    use_service_key=True
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


@router.get("/options/teacher-contracts/{teacher_id}", tags=["預約管理"])
async def get_teacher_contract_options(
    teacher_id: str,
    current_user: CurrentUser = Depends(get_current_user)
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
            use_service_key=True
        )
        return {"data": contracts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/teacher-slots/{teacher_id}", tags=["預約管理"])
async def get_teacher_slot_options(
    teacher_id: str,
    date_from: Optional[date] = Query(None, description="開始日期"),
    date_to: Optional[date] = Query(None, description="結束日期"),
    current_user: CurrentUser = Depends(get_current_user)
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
            use_service_key=True
        )

        # 如果有結束日期，在結果中篩選
        if date_to:
            slots = [s for s in slots if s.get("slot_date") <= date_to.isoformat()]

        return {"data": slots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


