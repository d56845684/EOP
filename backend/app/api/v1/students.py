from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_page_permission, get_user_employee_id
from app.schemas.student import (
    StudentCreate, StudentUpdate, StudentResponse, StudentListResponse,
    ConvertToFormalRequest, ConvertToFormalResponse, ConvertToFormalContractInfo,
)
from app.schemas.student_view import StudentViewResponse
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime, date
import math
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/students", tags=["學生管理"])

STUDENT_SELECT = "id,student_no,name,eng_name,email,phone,address,birth_date,student_type,student_status,is_active,email_verified_at,created_at,updated_at"


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

        # 2. 更新 student_type → formal, student_status → active
        updated_student = await supabase_service.table_update(
            table="students",
            data={"student_type": "formal", "student_status": "active"},
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
            "total_leave_allowed": math.ceil(data.total_lessons * 0.2),
            "notes": data.notes,
        }
        if employee_id:
            contract_data["created_by"] = employee_id

        contract = await supabase_service.table_insert(
            table="student_contracts", data=contract_data
        )
        if not contract:
            raise HTTPException(status_code=500, detail="建立合約失敗")

        # 4. 若提供 teacher_id，記錄轉正差額獎金
        #    差額 = trial_to_formal_bonus - trial_completed_bonus
        #    （試上完成獎金已在 booking completed 時發放）
        bonus_recorded = False
        bonus_amount = None
        if data.teacher_id:
            try:
                tc_list = await supabase_service.table_select(
                    table="teacher_contracts",
                    select="id,trial_to_formal_bonus,trial_completed_bonus",
                    filters={
                        "teacher_id": data.teacher_id,
                        "contract_status": "eq.active",
                        "is_deleted": "eq.false",
                    },
                )
                if tc_list:
                    formal_bonus = float(tc_list[0].get("trial_to_formal_bonus", 0) or 0)
                    completed_bonus = float(tc_list[0].get("trial_completed_bonus", 0) or 0)
                    bonus_amount = formal_bonus - completed_bonus
                    if bonus_amount < 0:
                        bonus_amount = 0
                    bonus_recorded = True
                    # 寫入差額獎金紀錄
                    try:
                        bonus_data = {
                            "teacher_id": data.teacher_id,
                            "bonus_type": "trial_to_formal",
                            "amount": bonus_amount,
                            "bonus_date": date.today().isoformat(),
                            "description": f"學生 {student.get('name', '')} 試上轉正獎金（差額）",
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


# ============================================
# Student Overview — 學生總覽列表 API
# ============================================

@router.get("/overview/list")
async def list_students_overview(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    student_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    has_account: Optional[bool] = Query(None),
    has_active_contract: Optional[bool] = Query(None),
    role: Optional[str] = Query(None, description="角色篩選 (student/teacher/admin/employee)"),
    current_user: CurrentUser = Depends(require_page_permission("students.list"))
):
    """學生總覽列表：每位學生一行，附帶合約/預約/帳號摘要"""
    try:
        pool = supabase_service.pool

        # 動態 WHERE
        conditions = ["s.is_deleted = FALSE"]
        params: list = []
        idx = 0

        if search:
            idx += 1
            conditions.append(f"(s.student_no ILIKE ${idx} OR s.name ILIKE ${idx} OR s.email ILIKE ${idx})")
            params.append(f"%{search}%")
        if student_type:
            idx += 1
            conditions.append(f"s.student_type = ${idx}")
            params.append(student_type)
        if is_active is not None:
            idx += 1
            conditions.append(f"s.is_active = ${idx}")
            params.append(is_active)

        if role:
            idx += 1
            conditions.append(f"r.key = ${idx}")
            params.append(role)

        where_sql = " AND ".join(conditions)

        # 主查詢：學生 + 聚合摘要（一條 SQL）
        base_sql = f"""
            SELECT
                s.id, s.student_no, s.name, s.eng_name, s.email, s.phone,
                s.student_type, s.student_status, s.is_active, s.email_verified_at, s.created_at,
                -- 帳號
                (up.id IS NOT NULL) AS has_account,
                up.is_active AS account_active,
                r.key AS role,
                -- LINE
                (lb.id IS NOT NULL) AS line_bound,
                lb.line_display_name,
                -- 合約摘要
                COALESCE(ct.total_contracts, 0) AS total_contracts,
                COALESCE(ct.active_contracts, 0) AS active_contracts,
                COALESCE(ct.total_remaining, 0) AS remaining_lessons,
                -- 預約摘要
                COALESCE(bk.total_bookings, 0) AS total_bookings,
                COALESCE(bk.completed_bookings, 0) AS completed_bookings,
                COALESCE(bk.upcoming_bookings, 0) AS upcoming_bookings
            FROM students s
            LEFT JOIN user_profiles up ON up.student_id = s.id
            LEFT JOIN roles r ON r.id = up.role_id
            LEFT JOIN LATERAL (
                SELECT id, line_display_name
                FROM line_user_bindings
                WHERE user_id = up.id AND channel_type = 'student' AND binding_status = 'active'
                LIMIT 1
            ) lb ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(*) AS total_contracts,
                    COUNT(*) FILTER (WHERE contract_status = 'active') AS active_contracts,
                    COALESCE(SUM(remaining_lessons) FILTER (WHERE contract_status = 'active'), 0) AS total_remaining
                FROM student_contracts
                WHERE student_id = s.id AND is_deleted = FALSE
            ) ct ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(*) AS total_bookings,
                    COUNT(*) FILTER (WHERE booking_status = 'completed') AS completed_bookings,
                    COUNT(*) FILTER (WHERE booking_status IN ('pending','confirmed') AND booking_date >= CURRENT_DATE) AS upcoming_bookings
                FROM bookings
                WHERE student_id = s.id AND is_deleted = FALSE
            ) bk ON TRUE
            WHERE {where_sql}
        """

        # 後篩選（依賴聚合結果的條件）
        having_conditions = []
        if has_account is not None:
            if has_account:
                having_conditions.append("(up.id IS NOT NULL)")
            else:
                having_conditions.append("(up.id IS NULL)")
        if has_active_contract is not None:
            if has_active_contract:
                having_conditions.append("COALESCE(ct.active_contracts, 0) > 0")
            else:
                having_conditions.append("COALESCE(ct.active_contracts, 0) = 0")

        if having_conditions:
            base_sql += " AND " + " AND ".join(having_conditions)

        # Total count
        count_sql = f"SELECT COUNT(*) FROM ({base_sql}) sub"
        total = await pool.fetchval(count_sql, *params)

        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        # 分頁資料
        idx += 1
        limit_idx = idx
        idx += 1
        offset_idx = idx
        data_sql = f"{base_sql} ORDER BY s.created_at DESC LIMIT ${limit_idx} OFFSET ${offset_idx}"
        params.extend([per_page, offset])

        rows = await pool.fetch(data_sql, *params)

        items = []
        for row in rows:
            items.append({
                "id": str(row["id"]),
                "student_no": row["student_no"],
                "name": row["name"],
                "eng_name": row["eng_name"],
                "email": row["email"],
                "phone": row["phone"],
                "student_type": row["student_type"],
                "student_status": row["student_status"],
                "is_active": row["is_active"],
                "email_verified_at": row["email_verified_at"].isoformat() if row["email_verified_at"] else None,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "has_account": row["has_account"],
                "account_active": row["account_active"],
                "role": row["role"],
                "line_bound": row["line_bound"],
                "line_display_name": row["line_display_name"],
                "total_contracts": row["total_contracts"],
                "active_contracts": row["active_contracts"],
                "remaining_lessons": int(row["remaining_lessons"]),
                "total_bookings": row["total_bookings"],
                "completed_bookings": row["completed_bookings"],
                "upcoming_bookings": row["upcoming_bookings"],
            })

        return {
            "data": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"取得學生總覽失敗: {e}")
        raise HTTPException(status_code=500, detail=f"取得學生總覽失敗: {str(e)}")


# ============================================
# Student View — 學生綜合檢視 API
# ============================================

@router.get("/{student_id}/view", response_model=DataResponse[StudentViewResponse])
async def get_student_view(
    student_id: str,
    current_user: CurrentUser = Depends(require_page_permission("students.list"))
):
    """學生綜合檢視：一次取得該學生所有相關資料"""
    try:
        pool = supabase_service.pool
        sid = uuid.UUID(student_id)

        # ── 1. 學生基本資料 ──
        student_row = await pool.fetchrow(
            """SELECT id,student_no,name,eng_name,email,phone,address,birth_date,
                      student_type,is_active,email_verified_at,created_at
               FROM students WHERE id = $1 AND is_deleted = FALSE""",
            sid,
        )
        if not student_row:
            raise HTTPException(status_code=404, detail="學生不存在")

        student = dict(student_row)
        student["id"] = str(student["id"])

        # ── 2. 帳號狀態 ──
        account_row = await pool.fetchrow(
            """SELECT up.is_active, r.key AS role
               FROM user_profiles up
               JOIN roles r ON r.id = up.role_id
               WHERE up.student_id = $1""",
            sid,
        )
        account_info = {
            "has_account": account_row is not None,
            "is_active": account_row["is_active"] if account_row else None,
            "role": account_row["role"] if account_row else None,
        }

        # ── 3. LINE 綁定 ──
        line_row = await pool.fetchrow(
            """SELECT line_display_name, line_picture_url, binding_status
               FROM line_user_bindings
               WHERE user_id = (SELECT id FROM user_profiles WHERE student_id = $1 LIMIT 1)
                 AND channel_type = 'student'
               LIMIT 1""",
            sid,
        )
        line_info = {
            "bound": line_row is not None,
            "line_display_name": line_row["line_display_name"] if line_row else None,
            "line_picture_url": line_row["line_picture_url"] if line_row else None,
            "binding_status": line_row["binding_status"] if line_row else None,
        }

        # ── 4. 合約（含教師名、附約數） ──
        contract_rows = await pool.fetch(
            """SELECT sc.id, sc.contract_no, sc.contract_status,
                      sc.start_date, sc.end_date,
                      sc.total_lessons, sc.remaining_lessons, sc.total_amount,
                      sc.total_leave_allowed, sc.used_leave_count,
                      sc.used_emergency_leave_count, sc.is_recurring
               FROM student_contracts sc
               WHERE sc.student_id = $1 AND sc.is_deleted = FALSE
               ORDER BY sc.start_date DESC""",
            sid,
        )
        contracts = []
        for cr in contract_rows:
            cid = cr["id"]
            # 教師名（從該合約的預約記錄取得不重複教師）
            teacher_rows = await pool.fetch(
                """SELECT DISTINCT t.name FROM bookings b
                   JOIN teachers t ON t.id = b.teacher_id
                   WHERE b.student_contract_id = $1 AND b.is_deleted = FALSE""",
                cid,
            )
            # 附約數
            addendum_count = await pool.fetchval(
                """SELECT COUNT(*) FROM contract_addendums
                   WHERE contract_type = 'student' AND parent_contract_id = $1
                     AND is_deleted = FALSE""",
                cid,
            )
            c = dict(cr)
            c["id"] = str(cid)
            c["teachers"] = [r["name"] for r in teacher_rows]
            c["addendum_count"] = addendum_count or 0
            if c.get("total_amount") is not None:
                c["total_amount"] = float(c["total_amount"])
            contracts.append(c)

        # ── 5. 預約（最近 20 筆） ──
        booking_rows = await pool.fetch(
            """SELECT b.id, b.booking_date, b.start_time, b.end_time,
                      b.booking_status, b.booking_type,
                      t.name AS teacher_name, c.course_name AS course_name
               FROM bookings b
               LEFT JOIN teachers t ON t.id = b.teacher_id
               LEFT JOIN courses c ON c.id = b.course_id
               WHERE b.student_id = $1 AND b.is_deleted = FALSE
               ORDER BY b.booking_date DESC, b.start_time DESC
               LIMIT 20""",
            sid,
        )
        bookings_recent = []
        for br in booking_rows:
            b = dict(br)
            b["id"] = str(b["id"])
            b["start_time"] = b["start_time"].strftime("%H:%M") if b["start_time"] else None
            b["end_time"] = b["end_time"].strftime("%H:%M") if b["end_time"] else None
            bookings_recent.append(b)

        # ── 6. 選課 ──
        course_rows = await pool.fetch(
            """SELECT sc.id, sc.course_id, c.course_name AS course_name,
                      c.course_code, sc.enrolled_at
               FROM student_courses sc
               JOIN courses c ON c.id = sc.course_id
               WHERE sc.student_id = $1 AND sc.is_deleted = FALSE
               ORDER BY sc.enrolled_at DESC""",
            sid,
        )
        courses = [
            {**dict(r), "id": str(r["id"]), "course_id": str(r["course_id"])}
            for r in course_rows
        ]

        # ── 7. 教師偏好 ──
        pref_rows = await pool.fetch(
            """SELECT stp.id, c.course_name AS course_name,
                      stp.min_teacher_level,
                      t.name AS primary_teacher_name
               FROM student_teacher_preferences stp
               LEFT JOIN courses c ON c.id = stp.course_id
               LEFT JOIN teachers t ON t.id = stp.primary_teacher_id
               WHERE stp.student_id = $1 AND stp.is_deleted = FALSE""",
            sid,
        )
        preferences = [
            {**dict(r), "id": str(r["id"])}
            for r in pref_rows
        ]

        # ── 8. 請假記錄（最近 10 筆） ──
        leave_rows = await pool.fetch(
            """SELECT lr.id, lr.leave_date, lr.leave_status, lr.leave_type,
                      lr.reason, b.booking_date
               FROM leave_records lr
               LEFT JOIN bookings b ON b.id = lr.booking_id
               WHERE lr.initiator_student_id = $1 AND lr.is_deleted = FALSE
               ORDER BY lr.leave_date DESC
               LIMIT 10""",
            sid,
        )
        leave_records = [
            {**dict(r), "id": str(r["id"])}
            for r in leave_rows
        ]

        # ── 9. 統計 ──
        stats_row = await pool.fetchrow(
            """SELECT
                 COUNT(*) FILTER (WHERE is_deleted = FALSE) AS total_bookings,
                 COUNT(*) FILTER (WHERE booking_status = 'completed' AND is_deleted = FALSE) AS completed_bookings,
                 COUNT(*) FILTER (WHERE booking_status = 'cancelled' AND is_deleted = FALSE) AS cancelled_bookings,
                 COUNT(*) FILTER (WHERE booking_status = 'pending' AND is_deleted = FALSE) AS pending_bookings,
                 COUNT(*) FILTER (WHERE booking_status IN ('pending','confirmed')
                                    AND booking_date >= CURRENT_DATE AND is_deleted = FALSE) AS upcoming_bookings
               FROM bookings WHERE student_id = $1""",
            sid,
        )
        contract_stats = await pool.fetchrow(
            """SELECT
                 COUNT(*) AS total_contracts,
                 COUNT(*) FILTER (WHERE contract_status = 'active') AS active_contracts,
                 COALESCE(SUM(remaining_lessons) FILTER (WHERE contract_status = 'active'), 0) AS total_remaining_lessons,
                 COALESCE(SUM(used_leave_count), 0) AS total_leaves_used
               FROM student_contracts
               WHERE student_id = $1 AND is_deleted = FALSE""",
            sid,
        )
        course_count = await pool.fetchval(
            "SELECT COUNT(*) FROM student_courses WHERE student_id = $1 AND is_deleted = FALSE",
            sid,
        )
        stats = {
            "total_bookings": stats_row["total_bookings"],
            "completed_bookings": stats_row["completed_bookings"],
            "cancelled_bookings": stats_row["cancelled_bookings"],
            "pending_bookings": stats_row["pending_bookings"],
            "upcoming_bookings": stats_row["upcoming_bookings"],
            "total_contracts": contract_stats["total_contracts"],
            "active_contracts": contract_stats["active_contracts"],
            "total_remaining_lessons": int(contract_stats["total_remaining_lessons"]),
            "total_leaves_used": int(contract_stats["total_leaves_used"]),
            "total_courses_enrolled": course_count or 0,
        }

        return DataResponse(
            data=StudentViewResponse(
                student=student,
                account=account_info,
                line_binding=line_info,
                contracts=contracts,
                bookings_recent=bookings_recent,
                courses=courses,
                teacher_preferences=preferences,
                leave_records_recent=leave_records,
                stats=stats,
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"取得學生綜合檢視失敗: {e}")
        raise HTTPException(status_code=500, detail=f"取得學生綜合檢視失敗: {str(e)}")
