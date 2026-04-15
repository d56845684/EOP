from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from app.services.supabase_service import supabase_service
from app.services.storage_service import storage_service
from app.config import settings
from app.core.dependencies import get_current_user, CurrentUser, require_staff, require_teacher, require_page_permission, get_user_employee_id
from app.schemas.teacher import TeacherCreate, TeacherUpdate, TeacherResponse, TeacherListResponse
from app.schemas.teacher_view import TeacherViewResponse
from app.schemas.response import BaseResponse, DataResponse
from typing import Optional
from datetime import datetime
import logging
import math
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teachers", tags=["教師管理"])

TEACHER_SELECT = "id,teacher_no,name,email,phone,address,bio,avatar_url,teacher_level,is_active,email_verified_at,created_at,updated_at"


async def _sign_avatar(raw_path: str | None) -> str | None:
    """將 S3 raw path 轉成 signed download URL，無頭像則回傳 None"""
    if not raw_path:
        return None
    return await storage_service.create_signed_download_url(
        bucket=settings.AWS_S3_BUCKET, path=raw_path, expires_in=3600,
    )


@router.get("", response_model=TeacherListResponse)
async def list_teachers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜尋（編號/姓名/email）"),
    is_active: Optional[bool] = Query(None),
    current_user: CurrentUser = Depends(require_page_permission("teachers.list"))
):
    """取得教師列表"""
    try:
        filters = {"is_deleted": "eq.false"}
        if is_active is not None:
            filters["is_active"] = f"eq.{str(is_active).lower()}"

        total = await supabase_service.table_count(table="teachers", filters=filters)
        total_pages = math.ceil(total / per_page) if total > 0 else 1
        offset = (page - 1) * per_page

        teachers = await supabase_service.table_select_with_pagination(
            table="teachers", select=TEACHER_SELECT, filters=filters,
            order_by="created_at.desc", limit=per_page, offset=offset
        )

        if search:
            s = search.lower()
            teachers = [
                t for t in teachers
                if s in t.get("teacher_no", "").lower()
                or s in t.get("name", "").lower()
                or s in t.get("email", "").lower()
            ]

        for t in teachers:
            t["avatar_url"] = await _sign_avatar(t.get("avatar_url"))

        return TeacherListResponse(
            data=[TeacherResponse(**t) for t in teachers],
            total=total, page=page, per_page=per_page, total_pages=total_pages
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師列表失敗: {str(e)}")


# ========== 教師自我更新（必須在 /{teacher_id} 之前定義）==========

class TeacherSelfUpdate(BaseModel):
    """教師自行更新的欄位"""
    bio: Optional[str] = Field(None, description="簡介")
    phone: Optional[str] = Field(None, max_length=20, description="電話")
    address: Optional[str] = Field(None, description="地址")


@router.put("/me", response_model=DataResponse[TeacherResponse])
async def update_teacher_self(
    data: TeacherSelfUpdate,
    current_user: CurrentUser = Depends(require_teacher)
):
    """教師更新自己的資料（bio/phone/address）"""
    try:
        # 從 user_profiles 取得 teacher_id
        profiles = await supabase_service.table_select(
            table="user_profiles",
            select="teacher_id",
            filters={"id": current_user.user_id},
        )
        if not profiles or not profiles[0].get("teacher_id"):
            raise HTTPException(status_code=403, detail="找不到對應的教師資料")

        teacher_id = profiles[0]["teacher_id"]

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="teachers", data=update_data,
            filters={"id": teacher_id, "is_deleted": "eq.false"},
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新教師資料失敗")

        return DataResponse(message="教師資料更新成功", data=TeacherResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新教師資料失敗: {str(e)}")


# ============================================
# Teacher Overview — 教師總覽列表
# （必須在 /{teacher_id} 之前註冊）
# ============================================

@router.get("/overview/list")
async def list_teachers_overview(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    has_account: Optional[bool] = Query(None),
    has_active_contract: Optional[bool] = Query(None),
    role: Optional[str] = Query(None, description="角色篩選 (student/teacher/admin/employee)"),
    current_user: CurrentUser = Depends(require_page_permission("teachers.list"))
):
    """教師總覽列表：每位教師一行，附帶合約/預約/帳號/獎金摘要"""
    try:
        pool = supabase_service.pool

        # 動態 WHERE
        conditions = ["t.is_deleted = FALSE"]
        params: list = []
        idx = 0

        if search:
            idx += 1
            conditions.append(f"(t.teacher_no ILIKE ${idx} OR t.name ILIKE ${idx} OR t.email ILIKE ${idx})")
            params.append(f"%{search}%")
        if is_active is not None:
            idx += 1
            conditions.append(f"t.is_active = ${idx}")
            params.append(is_active)
        if role:
            idx += 1
            conditions.append(f"r.key = ${idx}")
            params.append(role)

        where_sql = " AND ".join(conditions)

        base_sql = f"""
            SELECT
                t.id, t.teacher_no, t.name, t.email, t.phone,
                t.avatar_url,
                t.teacher_level, t.is_active, t.email_verified_at, t.created_at,
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
                -- 預約摘要
                COALESCE(bk.total_bookings, 0) AS total_bookings,
                COALESCE(bk.completed_bookings, 0) AS completed_bookings,
                COALESCE(bk.upcoming_bookings, 0) AS upcoming_bookings,
                -- 獎金摘要
                COALESCE(bn.total_bonus, 0) AS total_bonus,
                COALESCE(bn.bonus_count, 0) AS bonus_count
            FROM teachers t
            LEFT JOIN user_profiles up ON up.teacher_id = t.id
            LEFT JOIN roles r ON r.id = up.role_id
            LEFT JOIN LATERAL (
                SELECT id, line_display_name
                FROM line_user_bindings
                WHERE user_id = up.id AND channel_type = 'teacher' AND binding_status = 'active'
                LIMIT 1
            ) lb ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(*) AS total_contracts,
                    COUNT(*) FILTER (WHERE contract_status = 'active') AS active_contracts
                FROM teacher_contracts
                WHERE teacher_id = t.id AND is_deleted = FALSE
            ) ct ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(*) AS total_bookings,
                    COUNT(*) FILTER (WHERE booking_status = 'completed') AS completed_bookings,
                    COUNT(*) FILTER (WHERE booking_status IN ('pending','confirmed') AND booking_date >= CURRENT_DATE) AS upcoming_bookings
                FROM bookings
                WHERE teacher_id = t.id AND is_deleted = FALSE
            ) bk ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    COALESCE(SUM(amount), 0) AS total_bonus,
                    COUNT(*) AS bonus_count
                FROM teacher_bonus_records
                WHERE teacher_id = t.id AND is_deleted = FALSE
            ) bn ON TRUE
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
        data_sql = f"{base_sql} ORDER BY t.created_at DESC LIMIT ${limit_idx} OFFSET ${offset_idx}"
        params.extend([per_page, offset])

        rows = await pool.fetch(data_sql, *params)

        items = []
        for row in rows:
            items.append({
                "id": str(row["id"]),
                "teacher_no": row["teacher_no"],
                "name": row["name"],
                "email": row["email"],
                "phone": row["phone"],
                "avatar_url": await _sign_avatar(row["avatar_url"]),
                "teacher_level": row["teacher_level"],
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
                "total_bookings": row["total_bookings"],
                "completed_bookings": row["completed_bookings"],
                "upcoming_bookings": row["upcoming_bookings"],
                "total_bonus": float(row["total_bonus"]),
                "bonus_count": row["bonus_count"],
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
        logger.exception(f"取得教師總覽失敗: {e}")
        raise HTTPException(status_code=500, detail=f"取得教師總覽失敗: {str(e)}")


@router.get("/{teacher_id}", response_model=DataResponse[TeacherResponse])
async def get_teacher(
    teacher_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.list"))
):
    """取得單一教師"""
    try:
        result = await supabase_service.table_select(
            table="teachers", select=TEACHER_SELECT,
            filters={"id": teacher_id, "is_deleted": "eq.false"}
        )
        if not result:
            raise HTTPException(status_code=404, detail="教師不存在")
        result[0]["avatar_url"] = await _sign_avatar(result[0].get("avatar_url"))
        return DataResponse(data=TeacherResponse(**result[0]))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得教師失敗: {str(e)}")


@router.post("", response_model=DataResponse[TeacherResponse])
async def create_teacher(
    data: TeacherCreate,
    current_user: CurrentUser = Depends(require_page_permission("teachers.create"))
):
    """建立教師（僅限員工）"""
    try:
        # 自動產生 EOPT 編號
        if not data.teacher_no:
            pool = supabase_service.pool
            row = await pool.fetchrow("SELECT nextval('teachers_eopt_seq') AS seq")
            data.teacher_no = f"EOPT{row['seq']}"

        existing = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"teacher_no": data.teacher_no, "is_deleted": "eq.false"}
        )
        if existing:
            raise HTTPException(status_code=400, detail="教師編號已存在")

        existing_email = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"email": data.email, "is_deleted": "eq.false"}
        )
        if existing_email:
            raise HTTPException(status_code=400, detail="Email 已存在")

        teacher_data = data.model_dump()
        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            teacher_data["created_by"] = employee_id

        result = await supabase_service.table_insert(
            table="teachers", data=teacher_data
        )
        if not result:
            raise HTTPException(status_code=500, detail="建立教師失敗")

        return DataResponse(message="教師建立成功", data=TeacherResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立教師失敗: {str(e)}")


@router.put("/{teacher_id}", response_model=DataResponse[TeacherResponse])
async def update_teacher(
    teacher_id: str,
    data: TeacherUpdate,
    current_user: CurrentUser = Depends(require_page_permission("teachers.edit"))
):
    """更新教師（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teachers", select="id,teacher_no,email",
            filters={"id": teacher_id, "is_deleted": "eq.false"}
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師不存在")

        if data.email and data.email != existing[0]["email"]:
            dup = await supabase_service.table_select(
                table="teachers", select="id",
                filters={"email": data.email, "is_deleted": "eq.false"}
            )
            if dup:
                raise HTTPException(status_code=400, detail="Email 已存在")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        result = await supabase_service.table_update(
            table="teachers", data=update_data, filters={"id": teacher_id}
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新教師失敗")

        return DataResponse(message="教師更新成功", data=TeacherResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新教師失敗: {str(e)}")


@router.delete("/{teacher_id}", response_model=BaseResponse)
async def delete_teacher(
    teacher_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.delete"))
):
    """刪除教師（軟刪除，僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"id": teacher_id, "is_deleted": "eq.false"}
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師不存在")

        result = await supabase_service.table_update(
            table="teachers",
            data={"is_deleted": True, "deleted_at": datetime.utcnow().isoformat()},
            filters={"id": teacher_id}
        )
        if not result:
            raise HTTPException(status_code=500, detail="刪除教師失敗")

        return BaseResponse(message="教師刪除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除教師失敗: {str(e)}")


# ========== 教師頭像上傳 ==========

# 頭像允許的圖片格式和大小限制
AVATAR_ALLOWED_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png", "webp": "image/webp",
}
AVATAR_MAX_SIZE = 2 * 1024 * 1024  # 2MB


class AvatarUploadUrlRequest(BaseModel):
    """取得頭像上傳連結請求"""
    file_name: str


class AvatarConfirmRequest(BaseModel):
    """確認頭像上傳請求"""
    storage_path: str
    file_name: str


@router.post("/{teacher_id}/avatar/upload-url")
async def get_teacher_avatar_upload_url(
    teacher_id: str,
    body: AvatarUploadUrlRequest,
    current_user: CurrentUser = Depends(require_page_permission("teachers.edit"))
):
    """取得教師頭像的 signed upload URL（僅限員工，支援 jpg/png/webp，最大 2MB）"""
    import os
    try:
        ext = os.path.splitext(body.file_name)[1].lower().lstrip(".")
        if ext not in AVATAR_ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail=f"不支援的圖片格式: {ext}（允許 jpg/png/webp）")

        existing = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"id": teacher_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師不存在")

        await storage_service.ensure_bucket_exists(settings.AWS_S3_BUCKET)

        safe_filename = f"{uuid.uuid4().hex}.{ext}"
        storage_path = f"teachers/{teacher_id}/avatar/{safe_filename}"

        signed = await storage_service.create_signed_upload_url(
            bucket=settings.AWS_S3_BUCKET,
            path=storage_path,
            content_type=AVATAR_ALLOWED_TYPES[ext],
            max_size_bytes=AVATAR_MAX_SIZE,
        )
        if not signed:
            raise HTTPException(status_code=500, detail="產生上傳連結失敗")

        return {
            "upload_url": signed["upload_url"],
            "storage_path": storage_path,
            "content_type": AVATAR_ALLOWED_TYPES[ext],
            "max_size_bytes": AVATAR_MAX_SIZE,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產生上傳連結失敗: {str(e)}")


@router.post("/{teacher_id}/avatar/confirm-upload", response_model=DataResponse[TeacherResponse])
async def confirm_teacher_avatar_upload(
    teacher_id: str,
    body: AvatarConfirmRequest,
    current_user: CurrentUser = Depends(require_page_permission("teachers.edit"))
):
    """確認教師頭像上傳完成（僅限員工）"""
    try:
        existing = await supabase_service.table_select(
            table="teachers", select="id",
            filters={"id": teacher_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise HTTPException(status_code=404, detail="教師不存在")

        # 驗證 S3 檔案存在
        file_exists = await storage_service.verify_file_exists(
            bucket=settings.AWS_S3_BUCKET,
            path=body.storage_path
        )
        if not file_exists:
            raise HTTPException(status_code=400, detail="檔案尚未上傳至 S3")

        # 產生 avatar_url（使用 S3 path）
        result = await supabase_service.table_update(
            table="teachers",
            data={"avatar_url": body.storage_path},
            filters={"id": teacher_id},
        )
        if not result:
            raise HTTPException(status_code=500, detail="更新頭像失敗")

        result["avatar_url"] = await _sign_avatar(result.get("avatar_url"))
        return DataResponse(message="頭像上傳成功", data=TeacherResponse(**result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"確認頭像上傳失敗: {str(e)}")


# ============================================
# Teacher View — 教師綜合檢視 API
# ============================================

@router.get("/{teacher_id}/view", response_model=DataResponse[TeacherViewResponse])
async def get_teacher_view(
    teacher_id: str,
    current_user: CurrentUser = Depends(require_page_permission("teachers.list"))
):
    """教師綜合檢視：一次取得該教師所有相關資料（已優化：並行查詢 + 統計合併）"""
    try:
        pool = supabase_service.pool
        tid = uuid.UUID(teacher_id)

        # ── 1. 教師基本資料 + 帳號 + LINE（合併為 1 query） ──
        teacher_row = await pool.fetchrow(
            """SELECT t.id, t.teacher_no, t.name, t.email, t.phone, t.address,
                      t.bio, t.avatar_url, t.teacher_level, t.is_active,
                      t.email_verified_at, t.created_at,
                      up.is_active AS account_active, r.key AS role,
                      lb.line_display_name, lb.line_picture_url, lb.binding_status
               FROM teachers t
               LEFT JOIN user_profiles up ON up.teacher_id = t.id
               LEFT JOIN roles r ON r.id = up.role_id
               LEFT JOIN LATERAL (
                   SELECT line_display_name, line_picture_url, binding_status
                   FROM line_user_bindings
                   WHERE user_id = up.id AND channel_type = 'teacher'
                   LIMIT 1
               ) lb ON TRUE
               WHERE t.id = $1 AND t.is_deleted = FALSE""",
            tid,
        )
        if not teacher_row:
            raise HTTPException(status_code=404, detail="教師不存在")

        r = teacher_row
        # avatar_url: S3 path → presigned URL
        teacher = {
            "id": str(r["id"]), "teacher_no": r["teacher_no"], "name": r["name"],
            "email": r["email"], "phone": r["phone"], "address": r["address"],
            "bio": r["bio"], "avatar_url": await _sign_avatar(r["avatar_url"]),
            "teacher_level": r["teacher_level"],
            "is_active": r["is_active"], "email_verified_at": r["email_verified_at"],
            "created_at": r["created_at"],
        }
        account_info = {
            "has_account": r["role"] is not None,
            "is_active": r["account_active"],
            "role": r["role"],
        }
        line_info = {
            "bound": r["line_display_name"] is not None,
            "line_display_name": r["line_display_name"],
            "line_picture_url": r["line_picture_url"],
            "binding_status": r["binding_status"],
        }

        # ── 2~6. 並行查詢（無依賴關係） ──
        import asyncio

        contracts_task = pool.fetch(
            """SELECT tc.id, tc.contract_no, tc.contract_status,
                      tc.start_date, tc.end_date, tc.employment_type, tc.notes,
                      COALESCE(ca.addendum_count, 0) AS addendum_count
               FROM teacher_contracts tc
               LEFT JOIN LATERAL (
                   SELECT COUNT(*) AS addendum_count
                   FROM contract_addendums
                   WHERE contract_type = 'teacher' AND parent_contract_id = tc.id
                     AND is_deleted = FALSE
               ) ca ON TRUE
               WHERE tc.teacher_id = $1 AND tc.is_deleted = FALSE
               ORDER BY tc.start_date DESC""",
            tid,
        )

        bookings_task = pool.fetch(
            """SELECT b.id, b.booking_date, b.start_time, b.end_time,
                      b.booking_status, b.booking_type,
                      s.name AS student_name, c.course_name AS course_name
               FROM bookings b
               LEFT JOIN students s ON s.id = b.student_id
               LEFT JOIN courses c ON c.id = b.course_id
               WHERE b.teacher_id = $1 AND b.is_deleted = FALSE
               ORDER BY b.booking_date DESC, b.start_time DESC
               LIMIT 20""",
            tid,
        )

        bonus_task = pool.fetch(
            """SELECT tbr.id, tbr.bonus_type, tbr.amount, tbr.bonus_date,
                      tbr.description, s.name AS student_name
               FROM teacher_bonus_records tbr
               LEFT JOIN students s ON s.id = tbr.related_student_id
               WHERE tbr.teacher_id = $1 AND tbr.is_deleted = FALSE
               ORDER BY tbr.bonus_date DESC
               LIMIT 20""",
            tid,
        )

        schedules_task = pool.fetch(
            """SELECT id, weekday, start_time, end_time, notes
               FROM teacher_work_schedules
               WHERE teacher_contract_id IN (
                   SELECT id FROM teacher_contracts
                   WHERE teacher_id = $1 AND contract_status = 'active' AND is_deleted = FALSE
               ) AND is_deleted = FALSE
               ORDER BY weekday, start_time""",
            tid,
        )

        # 統計：bookings 單次掃描 + FILTER，teacher_contracts / bonus 各掃一次（共 3 次而非 10 次）
        stats_task = pool.fetchrow(
            """WITH bk AS (
                   SELECT booking_status, booking_date, student_id
                   FROM bookings WHERE teacher_id = $1 AND is_deleted = FALSE
               )
               SELECT
                 (SELECT COUNT(*) FROM bk) AS total_bookings,
                 (SELECT COUNT(*) FROM bk WHERE booking_status = 'completed') AS completed_bookings,
                 (SELECT COUNT(*) FROM bk WHERE booking_status = 'cancelled') AS cancelled_bookings,
                 (SELECT COUNT(*) FROM bk WHERE booking_status = 'pending') AS pending_bookings,
                 (SELECT COUNT(*) FROM bk WHERE booking_status IN ('pending','confirmed')
                                            AND booking_date >= CURRENT_DATE) AS upcoming_bookings,
                 (SELECT COUNT(DISTINCT student_id) FROM bk WHERE booking_status = 'completed') AS total_students_taught,
                 (SELECT COUNT(*) FROM teacher_contracts
                  WHERE teacher_id = $1 AND is_deleted = FALSE) AS total_contracts,
                 (SELECT COUNT(*) FROM teacher_contracts
                  WHERE teacher_id = $1 AND is_deleted = FALSE AND contract_status = 'active') AS active_contracts,
                 (SELECT COALESCE(SUM(amount), 0) FROM teacher_bonus_records
                  WHERE teacher_id = $1 AND is_deleted = FALSE) AS total_bonus_amount,
                 (SELECT COUNT(*) FROM teacher_bonus_records
                  WHERE teacher_id = $1 AND is_deleted = FALSE) AS total_bonus_count""",
            tid,
        )

        contract_rows, booking_rows, bonus_rows, schedule_rows, stats_row = await asyncio.gather(
            contracts_task, bookings_task, bonus_task, schedules_task, stats_task
        )

        # ── 整理結果 ──
        contracts = [
            {**dict(cr), "id": str(cr["id"])}
            for cr in contract_rows
        ]

        bookings_recent = [
            {**dict(br), "id": str(br["id"]),
             "start_time": br["start_time"].strftime("%H:%M") if br["start_time"] else None,
             "end_time": br["end_time"].strftime("%H:%M") if br["end_time"] else None}
            for br in booking_rows
        ]

        bonus_records = [
            {**dict(br), "id": str(br["id"]),
             "amount": float(br["amount"]) if br.get("amount") is not None else None}
            for br in bonus_rows
        ]

        work_schedules = [
            {**dict(sr), "id": str(sr["id"]),
             "start_time": sr["start_time"].strftime("%H:%M") if sr["start_time"] else None,
             "end_time": sr["end_time"].strftime("%H:%M") if sr["end_time"] else None}
            for sr in schedule_rows
        ]

        stats = {
            "total_bookings": stats_row["total_bookings"],
            "completed_bookings": stats_row["completed_bookings"],
            "cancelled_bookings": stats_row["cancelled_bookings"],
            "pending_bookings": stats_row["pending_bookings"],
            "upcoming_bookings": stats_row["upcoming_bookings"],
            "total_contracts": stats_row["total_contracts"],
            "active_contracts": stats_row["active_contracts"],
            "total_bonus_amount": float(stats_row["total_bonus_amount"]),
            "total_bonus_count": stats_row["total_bonus_count"],
            "total_students_taught": stats_row["total_students_taught"],
        }

        return DataResponse(
            data=TeacherViewResponse(
                teacher=teacher,
                account=account_info,
                line_binding=line_info,
                contracts=contracts,
                bookings_recent=bookings_recent,
                bonus_records_recent=bonus_records,
                work_schedules=work_schedules,
                stats=stats,
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"取得教師綜合檢視失敗: {e}")
        raise HTTPException(status_code=500, detail=f"取得教師綜合檢視失敗: {str(e)}")
