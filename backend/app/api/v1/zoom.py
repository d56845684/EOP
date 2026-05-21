"""
Zoom 帳號池管理 + 會議操作 + 教師 OAuth + Webhook
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from app.services.supabase_service import supabase_service
from app.services.zoom_service import zoom_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, get_user_employee_id
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppException, bad_request, forbidden, not_found, internal_error
from app.schemas.zoom import (
    ZoomAccountCreate, ZoomAccountUpdate, ZoomAccountResponse, ZoomAccountListResponse,
    ZoomMeetingLogResponse, ZoomMeetingLogListResponse, ZoomMeetingCreateRequest,
    ZoomOAuthUrlResponse, ZoomTeacherLinkStatus,
    RecordingCallbackRequest,
    DownloadTokenRequest, DownloadTokenResponse,
)
from app.schemas.response import BaseResponse, DataResponse
from app.config import settings
from typing import Optional
from datetime import datetime, timezone, timedelta
import math
import logging
import json
import hashlib
import hmac

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/zoom", tags=["Zoom 管理"])

# 不暴露 secret 的欄位列表
ACCOUNT_SELECT = "id,account_name,zoom_account_id,zoom_client_id,zoom_user_email,account_tier,is_active,daily_meeting_count,daily_count_reset_at,notes,created_at,created_by,updated_at"

MEETING_LOG_SELECT = "id,booking_id,zoom_account_id,teacher_id,zoom_meeting_id,zoom_meeting_uuid,join_url,start_url,passcode,meeting_date,start_time,end_time,meeting_status,recording_url,recording_download_url,recording_file_type,recording_file_size_bytes,recording_duration_seconds,recording_completed_at,recording_transfer_status,drive_file_id,drive_view_link,transferred_at,created_at,updated_at"


# ============================================
# 帳號池 CRUD（require_staff）
# ============================================

@router.get("/accounts", response_model=ZoomAccountListResponse)
async def list_zoom_accounts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    current_user: CurrentUser = Depends(require_staff),
):
    """列出所有 Zoom 帳號"""
    try:
        filters: dict = {"is_deleted": "eq.false"}
        if is_active is not None:
            filters["is_active"] = f"eq.{str(is_active).lower()}"

        # 計算 total
        total = await supabase_service.table_count(table="zoom_accounts", filters=filters)
        total_pages = math.ceil(total / per_page) if total > 0 else 1

        items = await supabase_service.table_select_with_pagination(
            table="zoom_accounts",
            select=ACCOUNT_SELECT,
            filters=filters,
            order_by="created_at.desc",
            limit=per_page,
            offset=(page - 1) * per_page,
        )

        return ZoomAccountListResponse(
            data=[ZoomAccountResponse(**item) for item in items],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

    except Exception as e:
        raise internal_error(f"取得 Zoom 帳號列表失敗: {str(e)}", ErrorCode.ZOOM_ACCOUNT_LIST_FAILED)


@router.post("/accounts", response_model=DataResponse[ZoomAccountResponse])
async def create_zoom_account(
    data: ZoomAccountCreate,
    current_user: CurrentUser = Depends(require_staff),
):
    """新增 Zoom 帳號"""
    try:
        employee_id = await get_user_employee_id(current_user.user_id)

        insert_data = data.model_dump()
        if employee_id:
            insert_data["created_by"] = employee_id
            insert_data["updated_by"] = employee_id

        result = await supabase_service.table_insert(
            table="zoom_accounts",
            data=insert_data,
        )

        if not result:
            raise internal_error("新增 Zoom 帳號失敗", ErrorCode.ZOOM_ACCOUNT_CREATE_FAILED)

        # 回傳不含 secret 的資料
        response_data = {k: v for k, v in result.items() if k != "zoom_client_secret"}
        return DataResponse(message="Zoom 帳號新增成功", data=ZoomAccountResponse(**response_data))

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"新增 Zoom 帳號失敗: {str(e)}", ErrorCode.ZOOM_ACCOUNT_CREATE_FAILED)


@router.put("/accounts/{account_id}", response_model=DataResponse[ZoomAccountResponse])
async def update_zoom_account(
    account_id: str,
    data: ZoomAccountUpdate,
    current_user: CurrentUser = Depends(require_staff),
):
    """更新 Zoom 帳號"""
    try:
        # 檢查是否存在
        existing = await supabase_service.table_select(
            table="zoom_accounts",
            select="id",
            filters={"id": account_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise AppException(404, "Zoom 帳號不存在", ErrorCode.ZOOM_ACCOUNT_NOT_FOUND)

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise bad_request("沒有要更新的資料", ErrorCode.ZOOM_NO_UPDATE_DATA)

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            update_data["updated_by"] = employee_id

        result = await supabase_service.table_update(
            table="zoom_accounts",
            data=update_data,
            filters={"id": account_id},
        )

        if not result:
            raise internal_error("更新 Zoom 帳號失敗", ErrorCode.ZOOM_ACCOUNT_UPDATE_FAILED)

        response_data = {k: v for k, v in result.items() if k != "zoom_client_secret"}
        return DataResponse(message="Zoom 帳號更新成功", data=ZoomAccountResponse(**response_data))

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"更新 Zoom 帳號失敗: {str(e)}", ErrorCode.ZOOM_ACCOUNT_UPDATE_FAILED)


@router.delete("/accounts/{account_id}", response_model=BaseResponse)
async def delete_zoom_account(
    account_id: str,
    current_user: CurrentUser = Depends(require_staff),
):
    """刪除 Zoom 帳號（軟刪除）"""
    try:
        existing = await supabase_service.table_select(
            table="zoom_accounts",
            select="id",
            filters={"id": account_id, "is_deleted": "eq.false"},
        )
        if not existing:
            raise AppException(404, "Zoom 帳號不存在", ErrorCode.ZOOM_ACCOUNT_NOT_FOUND)

        employee_id = await get_user_employee_id(current_user.user_id)
        delete_data: dict = {
            "is_deleted": True,
            "is_active": False,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }
        if employee_id:
            delete_data["deleted_by"] = employee_id

        await supabase_service.table_update(
            table="zoom_accounts",
            data=delete_data,
            filters={"id": account_id},
        )

        return BaseResponse(message="Zoom 帳號刪除成功")

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"刪除 Zoom 帳號失敗: {str(e)}", ErrorCode.ZOOM_ACCOUNT_DELETE_FAILED)


@router.post("/accounts/{account_id}/test", response_model=BaseResponse)
async def test_zoom_account(
    account_id: str,
    current_user: CurrentUser = Depends(require_staff),
):
    """測試 Zoom 帳號 S2S 連線"""
    try:
        accounts = await supabase_service.table_select(
            table="zoom_accounts",
            select="*",
            filters={"id": account_id, "is_deleted": "eq.false"},
        )
        if not accounts:
            raise AppException(404, "Zoom 帳號不存在", ErrorCode.ZOOM_ACCOUNT_NOT_FOUND)

        account = accounts[0]
        token = await zoom_service.get_s2s_token(account)

        if not token:
            raise bad_request("Zoom S2S 連線失敗，請檢查 Account ID / Client ID / Client Secret", ErrorCode.ZOOM_S2S_CONNECTION_FAILED)

        return BaseResponse(message="Zoom S2S 連線測試成功")

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"測試 Zoom 連線失敗: {str(e)}", ErrorCode.ZOOM_TEST_CONNECTION_FAILED)


# ============================================
# 會議操作
# ============================================

@router.post("/meetings/create", response_model=DataResponse[ZoomMeetingLogResponse])
async def create_zoom_meeting(
    data: ZoomMeetingCreateRequest,
    current_user: CurrentUser = Depends(require_staff),
):
    """手動為預約建立 Zoom 會議"""
    try:
        # 查詢預約資訊
        bookings = await supabase_service.table_select(
            table="bookings",
            select="id,teacher_id,booking_date,start_time,end_time,booking_status",
            filters={"id": data.booking_id, "is_deleted": "eq.false"},
        )
        if not bookings:
            raise not_found("預約", ErrorCode.ZOOM_BOOKING_NOT_FOUND)

        booking = bookings[0]

        if booking.get("booking_status") not in ("confirmed", "pending"):
            raise bad_request("只有待確認或已確認的預約可以建立 Zoom 會議", ErrorCode.ZOOM_BOOKING_STATUS_INVALID)

        from datetime import date as date_type, time as time_type, datetime as dt_type

        # 檢查是否為過去的預約
        booking_date_val = booking["booking_date"]
        start_time_val_check = booking["start_time"]
        if isinstance(booking_date_val, str):
            booking_date_val = date_type.fromisoformat(booking_date_val)
        if isinstance(start_time_val_check, str):
            start_time_val_check = time_type.fromisoformat(start_time_val_check)
        if dt_type.combine(booking_date_val, start_time_val_check) < dt_type.now():
            raise bad_request("無法為過去的預約建立 Zoom 會議", ErrorCode.ZOOM_BOOKING_IN_PAST)
        booking_date = booking["booking_date"]
        if isinstance(booking_date, str):
            booking_date = date_type.fromisoformat(booking_date)
        start_time = booking["start_time"]
        if isinstance(start_time, str):
            start_time = time_type.fromisoformat(start_time)
        end_time = booking["end_time"]
        if isinstance(end_time, str):
            end_time = time_type.fromisoformat(end_time)

        result = await zoom_service.create_meeting_for_booking(
            booking_id=data.booking_id,
            teacher_id=booking["teacher_id"],
            booking_date=booking_date,
            start_time_val=start_time,
            end_time_val=end_time,
        )

        if not result:
            raise internal_error("建立 Zoom 會議失敗，請確認帳號池是否有可用帳號", ErrorCode.ZOOM_MEETING_CREATE_FAILED)

        enriched = await enrich_meeting_log(result)
        return DataResponse(message="Zoom 會議建立成功", data=ZoomMeetingLogResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"建立 Zoom 會議失敗: {str(e)}", ErrorCode.ZOOM_MEETING_CREATE_FAILED)


@router.get("/meetings", response_model=ZoomMeetingLogListResponse)
async def list_zoom_meetings(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    meeting_status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_staff),
):
    """列出會議紀錄（Staff only）"""
    try:
        filters: dict = {"is_deleted": "eq.false"}
        if meeting_status:
            filters["meeting_status"] = f"eq.{meeting_status}"
        if date_from:
            filters["meeting_date"] = f"gte.{date_from}"
        if date_to:
            if "meeting_date" in filters:
                filters["meeting_date"] = filters["meeting_date"]
            else:
                filters["meeting_date"] = f"lte.{date_to}"

        # 計算 total
        total = await supabase_service.table_count(table="zoom_meeting_logs", filters=filters)
        total_pages = math.ceil(total / per_page) if total > 0 else 1

        items = await supabase_service.table_select_with_pagination(
            table="zoom_meeting_logs",
            select=MEETING_LOG_SELECT,
            filters=filters,
            order_by="meeting_date.desc,start_time.desc",
            limit=per_page,
            offset=(page - 1) * per_page,
        )

        # 批次 enrich（取代 N+1 迴圈）
        if items:
            account_ids = list({i["zoom_account_id"] for i in items if i.get("zoom_account_id")})
            teacher_ids = list({i["teacher_id"] for i in items if i.get("teacher_id")})

            import asyncio as _aio
            async def _empty(): return []
            acct_task = supabase_service.pool.fetch(
                "SELECT id, account_name FROM zoom_accounts WHERE id = ANY($1)", account_ids
            ) if account_ids else _empty()
            teacher_task = supabase_service.pool.fetch(
                "SELECT id, name FROM teachers WHERE id = ANY($1)", teacher_ids
            ) if teacher_ids else _empty()

            acct_rows, teacher_rows = await _aio.gather(acct_task, teacher_task)
            acct_map = {str(r["id"]): r["account_name"] for r in acct_rows}
            teacher_map = {str(r["id"]): r["name"] for r in teacher_rows}

            for item in items:
                item["account_name"] = acct_map.get(str(item.get("zoom_account_id")))
                item["teacher_name"] = teacher_map.get(str(item.get("teacher_id")))

        return ZoomMeetingLogListResponse(
            data=[ZoomMeetingLogResponse(**i) for i in items],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

    except Exception as e:
        raise internal_error(f"取得會議紀錄失敗: {str(e)}", ErrorCode.ZOOM_MEETING_LIST_FAILED)


@router.post("/meetings/batch")
async def batch_get_meetings_by_bookings(
    body: dict,
    current_user: CurrentUser = Depends(get_current_user),
):
    """批次查詢多筆預約的 Zoom 會議資訊（減少 N+1 請求）"""
    try:
        booking_ids = body.get("booking_ids", [])
        if not booking_ids or len(booking_ids) > 100:
            raise bad_request("booking_ids 必須為 1~100 筆", ErrorCode.ZOOM_BATCH_SIZE_INVALID)

        pool = supabase_service.pool

        # 權限過濾：非 staff 只能查自己的預約
        if not current_user.is_staff():
            if current_user.is_teacher():
                allowed = await pool.fetch(
                    """SELECT id FROM bookings
                       WHERE id = ANY($1) AND is_deleted = FALSE
                         AND (teacher_id = $2 OR id IN (
                           SELECT b.id FROM bookings b
                           JOIN substitute_details sd ON sd.id = b.substitute_detail_id
                           WHERE sd.substitute_teacher_id = $2 AND sd.is_deleted = FALSE
                         ))""",
                    booking_ids, current_user.teacher_id,
                )
            elif current_user.is_student():
                allowed = await pool.fetch(
                    "SELECT id FROM bookings WHERE id = ANY($1) AND is_deleted = FALSE AND student_id = $2",
                    booking_ids, current_user.student_id,
                )
            else:
                allowed = []
            booking_ids = [str(r["id"]) for r in allowed]
            if not booking_ids:
                return {"success": True, "message": "操作成功", "data": {}}

        # 一次查全部 zoom meeting logs
        rows = await pool.fetch(
            f"""SELECT {MEETING_LOG_SELECT}
                FROM zoom_meeting_logs
                WHERE booking_id = ANY($1)
                  AND is_deleted = FALSE
                  AND meeting_status != 'cancelled'
                ORDER BY created_at DESC""",
            booking_ids,
        )

        # 批次 enrich account_name / teacher_name
        account_ids = list({r["zoom_account_id"] for r in rows if r.get("zoom_account_id")})
        teacher_ids = list({r["teacher_id"] for r in rows if r.get("teacher_id")})

        import asyncio as _aio
        async def _empty(): return []
        acct_task = pool.fetch(
            "SELECT id, account_name FROM zoom_accounts WHERE id = ANY($1)", account_ids
        ) if account_ids else _empty()
        teacher_task = pool.fetch(
            "SELECT id, name FROM teachers WHERE id = ANY($1)", teacher_ids
        ) if teacher_ids else _empty()

        acct_rows, teacher_rows = await _aio.gather(acct_task, teacher_task)
        acct_map = {str(r["id"]): r["account_name"] for r in acct_rows}
        teacher_map = {str(r["id"]): r["name"] for r in teacher_rows}

        # 組成 booking_id → meeting info 的 map（每個 booking 取最新一筆）
        result = {}
        for row in rows:
            bid = str(row["booking_id"])
            if bid in result:
                continue  # 已有更新的紀錄（ORDER BY created_at DESC）
            item = dict(row)
            item["id"] = str(item["id"])
            item["booking_id"] = bid
            if item.get("zoom_account_id"):
                item["zoom_account_id"] = str(item["zoom_account_id"])
            if item.get("teacher_id"):
                item["teacher_id"] = str(item["teacher_id"])
            item["account_name"] = acct_map.get(str(row.get("zoom_account_id")))
            item["teacher_name"] = teacher_map.get(str(row.get("teacher_id")))
            # start_url 含 ZAK，等同 host 完整權限，僅 staff 可見
            if not current_user.is_staff():
                item["start_url"] = None
            result[bid] = ZoomMeetingLogResponse(**item).model_dump(mode="json")

        return {"success": True, "message": "操作成功", "data": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("批次查詢 Zoom 會議失敗")
        raise internal_error(f"批次查詢失敗: {str(e)}", ErrorCode.ZOOM_BATCH_QUERY_FAILED)


@router.get("/meetings/{booking_id}", response_model=DataResponse[ZoomMeetingLogResponse])
async def get_meeting_by_booking(
    booking_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """查詢預約的 Zoom 會議（教師/學生可查自己的）"""
    try:
        # 權限檢查
        if not current_user.is_staff():
            bookings = await supabase_service.table_select(
                table="bookings",
                select="id,teacher_id,student_id,substitute_detail_id",
                filters={"id": booking_id, "is_deleted": "eq.false"},
            )
            if not bookings:
                raise not_found("預約", ErrorCode.ZOOM_BOOKING_NOT_FOUND)

            booking = bookings[0]
            if current_user.is_teacher():
                is_original = booking.get("teacher_id") == current_user.teacher_id
                is_substitute = False
                if booking.get("substitute_detail_id"):
                    sd = await supabase_service.table_select(
                        table="substitute_details", select="substitute_teacher_id",
                        filters={"id": booking["substitute_detail_id"], "is_deleted": "eq.false"},
                    )
                    is_substitute = bool(sd and sd[0].get("substitute_teacher_id") == current_user.teacher_id)
                if not (is_original or is_substitute):
                    raise forbidden("無權查看此預約的 Zoom 資訊", ErrorCode.ZOOM_FORBIDDEN_VIEW_BOOKING)
            elif current_user.is_student():
                if booking.get("student_id") != current_user.student_id:
                    raise forbidden("無權查看此預約的 Zoom 資訊", ErrorCode.ZOOM_FORBIDDEN_VIEW_BOOKING)

        # 查詢會議
        logs = await supabase_service.table_select(
            table="zoom_meeting_logs",
            select=MEETING_LOG_SELECT,
            filters={
                "booking_id": booking_id,
                "is_deleted": "eq.false",
                "meeting_status": "neq.cancelled",
            },
        )

        if not logs:
            raise AppException(404, "此預約尚無 Zoom 會議", ErrorCode.ZOOM_NO_MEETING_FOR_BOOKING)

        enriched = await enrich_meeting_log(logs[0])
        # start_url 含 ZAK，等同 host 完整權限，僅 staff 可見
        if not current_user.is_staff():
            enriched["start_url"] = None
        return DataResponse(data=ZoomMeetingLogResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"查詢 Zoom 會議失敗: {str(e)}", ErrorCode.ZOOM_MEETING_QUERY_FAILED)


@router.post("/meetings/{booking_id}/fetch-recording", response_model=DataResponse[ZoomMeetingLogResponse])
async def fetch_recording(
    booking_id: str,
    current_user: CurrentUser = Depends(require_staff),
):
    """手動從 Zoom API 取得會議錄影資訊（僅限員工）"""
    try:
        # 確認 booking 存在
        bookings = await supabase_service.table_select(
            table="bookings",
            select="id,booking_status",
            filters={"id": booking_id, "is_deleted": "eq.false"},
        )
        if not bookings:
            raise not_found("預約", ErrorCode.ZOOM_BOOKING_NOT_FOUND)

        result = await zoom_service.fetch_meeting_recording(booking_id)
        if not result:
            raise AppException(404, "尚無可用的錄影，請確認會議已結束且有雲端錄影", ErrorCode.ZOOM_RECORDING_NOT_READY)

        # 重新查詢完整資料
        logs = await supabase_service.table_select(
            table="zoom_meeting_logs",
            select=MEETING_LOG_SELECT,
            filters={"booking_id": booking_id, "is_deleted": "eq.false"},
        )
        if not logs:
            raise internal_error("錄影資訊更新失敗", ErrorCode.ZOOM_RECORDING_UPDATE_FAILED)

        enriched = await enrich_meeting_log(logs[0])
        return DataResponse(message="錄影資訊取得成功", data=ZoomMeetingLogResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"取得錄影失敗: {str(e)}", ErrorCode.ZOOM_RECORDING_GET_FAILED)


# ============================================
# 教師 OAuth
# ============================================

@router.get("/oauth/authorize", response_model=ZoomOAuthUrlResponse)
async def get_oauth_authorize_url(
    current_user: CurrentUser = Depends(get_current_user),
):
    """取得 Zoom OAuth 授權 URL（教師綁定用）"""
    if not settings.zoom_oauth_configured:
        raise bad_request("Zoom OAuth 尚未設定", ErrorCode.ZOOM_OAUTH_NOT_CONFIGURED)

    state = current_user.user_id
    url = zoom_service.get_oauth_authorize_url(state=state)
    return ZoomOAuthUrlResponse(authorize_url=url)


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(""),
):
    """Zoom OAuth callback，存 token 到 teacher_zoom_accounts 表"""
    if not settings.zoom_oauth_configured:
        raise bad_request("Zoom OAuth 尚未設定", ErrorCode.ZOOM_OAUTH_NOT_CONFIGURED)

    # 換取 token
    token_data = await zoom_service.exchange_code_for_token(code)
    if not token_data:
        raise bad_request("Zoom OAuth token 換取失敗", ErrorCode.ZOOM_OAUTH_TOKEN_FAILED)

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)

    # 取得 Zoom 使用者資訊
    user_info = await zoom_service.get_zoom_user_info(access_token)
    zoom_user_id = user_info.get("id", "") if user_info else ""
    zoom_email = user_info.get("email", "") if user_info else ""

    # 用 state (user_id) 找到對應的 teacher
    if not state:
        raise bad_request("缺少 state 參數", ErrorCode.ZOOM_OAUTH_STATE_MISSING)

    # 根據 user_id 直接從 user_profiles 取 teacher_id
    profile = await supabase_service.table_select(
        table="user_profiles",
        select="teacher_id",
        filters={"id": state},
    )
    if not profile or not profile[0].get("teacher_id"):
        raise AppException(404, "找不到對應的教師紀錄", ErrorCode.ZOOM_TEACHER_NOT_FOUND_OAUTH)

    teacher_id = profile[0]["teacher_id"]
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    zoom_data = {
        "zoom_access_token": access_token,
        "zoom_refresh_token": refresh_token,
        "zoom_token_expires_at": expires_at.isoformat(),
        "zoom_user_id": zoom_user_id,
        "zoom_email": zoom_email,
        "zoom_linked_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
    }

    # 檢查是否已有紀錄（upsert）
    existing = await supabase_service.table_select(
        table="teacher_zoom_accounts",
        select="id",
        filters={"teacher_id": teacher_id},
    )
    if existing:
        zoom_data["is_deleted"] = False
        await supabase_service.table_update(
            table="teacher_zoom_accounts",
            data=zoom_data,
            filters={"teacher_id": teacher_id},
        )
    else:
        zoom_data["teacher_id"] = teacher_id
        await supabase_service.table_insert(
            table="teacher_zoom_accounts",
            data=zoom_data,
        )

    # 重導到前端
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/profile?zoom=linked")


@router.delete("/oauth/unlink", response_model=BaseResponse)
async def unlink_zoom(
    current_user: CurrentUser = Depends(get_current_user),
):
    """教師解除 Zoom 綁定"""
    teachers = await supabase_service.table_select(
        table="teachers",
        select="id",
        filters={"email": current_user.email},
    )
    if not teachers:
        raise AppException(404, "找不到教師紀錄", ErrorCode.ZOOM_TEACHER_NOT_FOUND)

    await supabase_service.table_update(
        table="teacher_zoom_accounts",
        data={
            "is_active": False,
            "is_deleted": True,
            "zoom_access_token": None,
            "zoom_refresh_token": None,
            "zoom_token_expires_at": None,
        },
        filters={"teacher_id": teachers[0]["id"], "is_deleted": "eq.false"},
    )

    return BaseResponse(message="Zoom 綁定已解除")


@router.get("/oauth/status", response_model=ZoomTeacherLinkStatus)
async def get_zoom_link_status(
    current_user: CurrentUser = Depends(get_current_user),
):
    """查詢教師 Zoom 綁定狀態"""
    teachers = await supabase_service.table_select(
        table="teachers",
        select="id",
        filters={"email": current_user.email},
    )

    if not teachers:
        return ZoomTeacherLinkStatus(is_linked=False)

    records = await supabase_service.table_select(
        table="teacher_zoom_accounts",
        select="zoom_user_id,zoom_email,zoom_linked_at",
        filters={"teacher_id": teachers[0]["id"], "is_deleted": "eq.false"},
    )

    if not records or not records[0].get("zoom_user_id"):
        return ZoomTeacherLinkStatus(is_linked=False)

    record = records[0]
    return ZoomTeacherLinkStatus(
        is_linked=True,
        zoom_email=record.get("zoom_email"),
        zoom_user_id=record.get("zoom_user_id"),
        linked_at=record.get("zoom_linked_at"),
    )


# ============================================
# Webhook
# ============================================

@router.post("/webhook")
async def zoom_webhook(request: Request):
    """
    接收 Zoom Webhook（需 3 秒內回 200）
    處理事件：recording.completed, meeting.ended, meeting.started
    也處理 Zoom URL validation (endpoint.url_validation)
    """
    body = await request.body()

    try:
        payload = json.loads(body)
    except Exception:
        return {"status": "invalid payload"}

    event = payload.get("event", "")

    # Zoom URL validation challenge
    if event == "endpoint.url_validation":
        plain_token = payload.get("payload", {}).get("plainToken", "")
        secret = settings.ZOOM_WEBHOOK_SECRET_TOKEN
        if secret and plain_token:
            hash_value = hmac.new(
                secret.encode("utf-8"),
                plain_token.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            return {"plainToken": plain_token, "encryptedToken": hash_value}
        return {"plainToken": plain_token, "encryptedToken": ""}

    # 驗證 webhook 簽名
    timestamp = request.headers.get("x-zm-request-timestamp", "")
    signature = request.headers.get("x-zm-signature", "")

    if settings.ZOOM_WEBHOOK_SECRET_TOKEN:
        if not zoom_service.verify_webhook(body, timestamp, signature):
            logger.warning("Zoom webhook 簽名驗證失敗")
            return {"status": "invalid signature"}

    # 處理事件
    event_payload = payload.get("payload", {})

    if event == "recording.completed":
        await zoom_service.handle_recording_completed(event_payload)
    elif event == "meeting.ended":
        await zoom_service.handle_meeting_ended(event_payload)
    elif event == "meeting.started":
        await zoom_service.handle_meeting_started(event_payload)
    else:
        logger.info(f"Zoom webhook 未處理的事件: {event}")

    return {"status": "ok"}


# ============================================
# Internal: Lambda 取得 Zoom download token
# ============================================

@router.post("/internal/download-token", response_model=DataResponse[DownloadTokenResponse])
async def get_download_token(data: DownloadTokenRequest):
    """Lambda 呼叫：用 meeting_id 取得新的 Zoom token + 下載 URL（不需登入，靠 secret 驗證）"""
    if data.secret != settings.RECORDING_CALLBACK_SECRET:
        raise forbidden("Invalid secret", ErrorCode.ZOOM_INVALID_SECRET)

    try:
        # 查詢 meeting log 取得 zoom_account_id
        logs = await supabase_service.table_select(
            table="zoom_meeting_logs",
            select="zoom_meeting_id,zoom_account_id,teacher_id",
            filters={"zoom_meeting_id": f"text.{data.meeting_id}", "is_deleted": "eq.false"},
        )
        if not logs:
            raise AppException(404, "Meeting not found", ErrorCode.ZOOM_MEETING_NOT_FOUND)

        log = logs[0]

        # 取得 token
        token = await zoom_service._get_token_for_download(log)
        if not token:
            raise internal_error("無法取得 Zoom token", ErrorCode.ZOOM_TOKEN_FAILED)

        # 用新 token 呼叫 Zoom API 取得新的下載 URL
        import httpx as hx
        resp = await hx.AsyncClient().get(
            f"https://api.zoom.us/v2/meetings/{log['zoom_meeting_id']}/recordings",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.status_code != 200:
            raise AppException(resp.status_code, f"Zoom API 錯誤: {resp.text[:200]}", ErrorCode.ZOOM_RECORDING_GET_FAILED)

        recording_files = resp.json().get("recording_files", [])
        video = None
        for f in recording_files:
            if f.get("file_type") == "MP4" and f.get("recording_type") == "shared_screen_with_speaker_view":
                video = f
                break
        if not video:
            for f in recording_files:
                if f.get("file_type") == "MP4":
                    video = f
                    break
        if not video and recording_files:
            video = recording_files[0]
        if not video:
            raise AppException(404, "無可用錄影檔案", ErrorCode.ZOOM_NO_RECORDING_FILE)

        # 取得 Google Drive 設定
        from app.services.google_service import google_drive_service
        drive_config = await google_drive_service.get_drive_config()

        drive_mode = "sa"
        drive_access_token = None
        drive_folder_id = None

        if drive_config and drive_config.get("drive_mode") == "oauth":
            drive_mode = "oauth"
            drive_access_token = await google_drive_service.get_active_token()
            drive_folder_id = drive_config.get("drive_folder_id")
        elif drive_config:
            drive_folder_id = drive_config.get("drive_folder_id")

        # 組合會議名稱（與 Zoom 會議標題相同格式 + 時間戳）
        meeting_topic = None
        _student_drive_folder = None
        _student_type = None
        try:
            topic_rows = await supabase_service.pool.fetch(
                """SELECT z.meeting_date, z.start_time, b.booking_no,
                          c.course_name, s.name as student_name,
                          s.eng_name as student_eng_name,
                          s.student_type, s.google_drive_folder_id,
                          t.name as teacher_name
                   FROM zoom_meeting_logs z
                   JOIN bookings b ON z.booking_id = b.id
                   JOIN courses c ON b.course_id = c.id
                   JOIN students s ON b.student_id = s.id
                   JOIN teachers t ON b.teacher_id = t.id
                   WHERE z.zoom_meeting_id = $1 AND z.is_deleted = false
                   LIMIT 1""",
                log["zoom_meeting_id"]
            )
            if topic_rows:
                r = topic_rows[0]
                date_str = r["meeting_date"].isoformat() if r["meeting_date"] else ""
                time_str = r["start_time"].strftime("%H%M") if r["start_time"] else ""
                student_display = r["student_name"] or ""
                if r.get("student_eng_name"):
                    student_display += f"({r['student_eng_name']})"
                meeting_topic = f"[{r['booking_no']}] {r['course_name']} {student_display} {r['teacher_name']} {date_str} {time_str}"
                # 記錄學生 Drive 資料夾和類型供 Lambda 使用
                _student_drive_folder = r.get("google_drive_folder_id")
                _student_type = r.get("student_type")
        except Exception as e:
            logger.warning(f"取得會議名稱失敗: {e}")

        return DataResponse(data=DownloadTokenResponse(
            download_url=video.get("download_url", ""),
            access_token=token,
            meeting_topic=meeting_topic,
            drive_mode=drive_mode,
            drive_access_token=drive_access_token,
            drive_folder_id=drive_folder_id,
            student_drive_folder_id=_student_drive_folder,
            student_type=_student_type,
        ))

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error(f"取得下載 token 失敗: {str(e)}", ErrorCode.ZOOM_DOWNLOAD_TOKEN_FAILED)


# ============================================
# Recording Callback（Lambda → Backend）
# ============================================

@router.post("/recording-callback")
async def recording_callback(data: RecordingCallbackRequest):
    """Lambda 錄影轉移完成回呼（更新 Google Drive 資訊到 zoom_meeting_logs）"""
    if data.secret != settings.RECORDING_CALLBACK_SECRET:
        raise forbidden("Invalid secret", ErrorCode.ZOOM_INVALID_SECRET)

    update: dict = {"recording_transfer_status": data.status}
    if data.status == "completed":
        update["drive_file_id"] = data.drive_file_id
        update["drive_view_link"] = data.drive_view_link
        update["transferred_at"] = datetime.now(timezone.utc).isoformat()
    else:
        update["transfer_error"] = data.error

    await supabase_service.table_update(
        table="zoom_meeting_logs",
        data=update,
        filters={"zoom_meeting_id": f"text.{data.meeting_id}", "is_deleted": "eq.false"},
    )

    logger.info(f"recording-callback: meeting_id={data.meeting_id}, status={data.status}")
    return {"ok": True}


# ============================================
# Helper
# ============================================

async def enrich_meeting_log(record: dict) -> dict:
    """加入 account_name, teacher_name"""
    try:
        if record.get("zoom_account_id"):
            accounts = await supabase_service.table_select(
                table="zoom_accounts",
                select="account_name",
                filters={"id": record["zoom_account_id"]},
            )
            if accounts:
                record["account_name"] = accounts[0].get("account_name")
    except Exception:
        pass

    try:
        if record.get("teacher_id"):
            teachers = await supabase_service.table_select(
                table="teachers",
                select="name",
                filters={"id": record["teacher_id"]},
            )
            if teachers:
                record["teacher_name"] = teachers[0].get("name")
    except Exception:
        pass

    return record
