"""
Zoom 帳號池管理 + 會議操作 + 教師 OAuth + Webhook
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from app.services.supabase_service import supabase_service
from app.services.zoom_service import zoom_service
from app.core.dependencies import get_current_user, CurrentUser, require_staff, get_user_employee_id
from app.schemas.zoom import (
    ZoomAccountCreate, ZoomAccountUpdate, ZoomAccountResponse, ZoomAccountListResponse,
    ZoomMeetingLogResponse, ZoomMeetingLogListResponse, ZoomMeetingCreateRequest,
    ZoomOAuthUrlResponse, ZoomTeacherLinkStatus,
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
ACCOUNT_SELECT = "id,account_name,zoom_account_id,zoom_client_id,zoom_user_email,is_active,daily_meeting_count,daily_count_reset_at,notes,created_at,created_by,updated_at"

MEETING_LOG_SELECT = "id,booking_id,zoom_account_id,teacher_id,zoom_meeting_id,zoom_meeting_uuid,join_url,start_url,passcode,meeting_date,start_time,end_time,meeting_status,recording_url,recording_download_url,recording_file_type,recording_file_size_bytes,recording_duration_seconds,recording_completed_at,created_at,updated_at"


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
        all_records = await supabase_service.table_select(
            table="zoom_accounts", select="id",
            filters=filters,
        )
        total = len(all_records)
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
        raise HTTPException(status_code=500, detail=f"取得 Zoom 帳號列表失敗: {str(e)}")


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
            raise HTTPException(status_code=500, detail="新增 Zoom 帳號失敗")

        # 回傳不含 secret 的資料
        response_data = {k: v for k, v in result.items() if k != "zoom_client_secret"}
        return DataResponse(message="Zoom 帳號新增成功", data=ZoomAccountResponse(**response_data))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"新增 Zoom 帳號失敗: {str(e)}")


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
            raise HTTPException(status_code=404, detail="Zoom 帳號不存在")

        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="沒有要更新的資料")

        employee_id = await get_user_employee_id(current_user.user_id)
        if employee_id:
            update_data["updated_by"] = employee_id

        result = await supabase_service.table_update(
            table="zoom_accounts",
            data=update_data,
            filters={"id": account_id},
        )

        if not result:
            raise HTTPException(status_code=500, detail="更新 Zoom 帳號失敗")

        response_data = {k: v for k, v in result.items() if k != "zoom_client_secret"}
        return DataResponse(message="Zoom 帳號更新成功", data=ZoomAccountResponse(**response_data))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新 Zoom 帳號失敗: {str(e)}")


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
            raise HTTPException(status_code=404, detail="Zoom 帳號不存在")

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
        raise HTTPException(status_code=500, detail=f"刪除 Zoom 帳號失敗: {str(e)}")


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
            raise HTTPException(status_code=404, detail="Zoom 帳號不存在")

        account = accounts[0]
        token = await zoom_service.get_s2s_token(account)

        if not token:
            raise HTTPException(status_code=400, detail="Zoom S2S 連線失敗，請檢查 Account ID / Client ID / Client Secret")

        return BaseResponse(message="Zoom S2S 連線測試成功")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"測試 Zoom 連線失敗: {str(e)}")


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
            raise HTTPException(status_code=404, detail="預約不存在")

        booking = bookings[0]

        if booking.get("booking_status") not in ("confirmed", "pending"):
            raise HTTPException(status_code=400, detail="只有待確認或已確認的預約可以建立 Zoom 會議")

        from datetime import date as date_type, time as time_type
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
            raise HTTPException(status_code=500, detail="建立 Zoom 會議失敗，請確認帳號池是否有可用帳號")

        enriched = await enrich_meeting_log(result)
        return DataResponse(message="Zoom 會議建立成功", data=ZoomMeetingLogResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立 Zoom 會議失敗: {str(e)}")


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
        all_records = await supabase_service.table_select(
            table="zoom_meeting_logs", select="id",
            filters=filters,
        )
        total = len(all_records)
        total_pages = math.ceil(total / per_page) if total > 0 else 1

        items = await supabase_service.table_select_with_pagination(
            table="zoom_meeting_logs",
            select=MEETING_LOG_SELECT,
            filters=filters,
            order_by="meeting_date.desc,start_time.desc",
            limit=per_page,
            offset=(page - 1) * per_page,
        )

        enriched_items = []
        for item in items:
            enriched = await enrich_meeting_log(item)
            enriched_items.append(ZoomMeetingLogResponse(**enriched))

        return ZoomMeetingLogListResponse(
            data=enriched_items,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得會議紀錄失敗: {str(e)}")


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
                select="id,teacher_id,student_id",
                filters={"id": booking_id, "is_deleted": "eq.false"},
            )
            if not bookings:
                raise HTTPException(status_code=404, detail="預約不存在")

            booking = bookings[0]
            if current_user.is_teacher():
                from app.api.v1.bookings import get_user_teacher_id
                teacher_id = await get_user_teacher_id(current_user.user_id)
                if booking.get("teacher_id") != teacher_id:
                    raise HTTPException(status_code=403, detail="無權查看此預約的 Zoom 資訊")
            elif current_user.is_student():
                # 查 student_id
                students = await supabase_service.table_select(
                    table="students",
                    select="id",
                    filters={"email": current_user.email},
                )
                student_id = students[0]["id"] if students else None
                if booking.get("student_id") != student_id:
                    raise HTTPException(status_code=403, detail="無權查看此預約的 Zoom 資訊")

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
            raise HTTPException(status_code=404, detail="此預約尚無 Zoom 會議")

        enriched = await enrich_meeting_log(logs[0])
        return DataResponse(data=ZoomMeetingLogResponse(**enriched))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢 Zoom 會議失敗: {str(e)}")


# ============================================
# 教師 OAuth
# ============================================

@router.get("/oauth/authorize", response_model=ZoomOAuthUrlResponse)
async def get_oauth_authorize_url(
    current_user: CurrentUser = Depends(get_current_user),
):
    """取得 Zoom OAuth 授權 URL（教師綁定用）"""
    if not settings.zoom_oauth_configured:
        raise HTTPException(status_code=400, detail="Zoom OAuth 尚未設定")

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
        raise HTTPException(status_code=400, detail="Zoom OAuth 尚未設定")

    # 換取 token
    token_data = await zoom_service.exchange_code_for_token(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Zoom OAuth token 換取失敗")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)

    # 取得 Zoom 使用者資訊
    user_info = await zoom_service.get_zoom_user_info(access_token)
    zoom_user_id = user_info.get("id", "") if user_info else ""
    zoom_email = user_info.get("email", "") if user_info else ""

    # 用 state (user_id) 找到對應的 teacher
    if not state:
        raise HTTPException(status_code=400, detail="缺少 state 參數")

    # 根據 user_id 找 teacher
    users_profile = await supabase_service.table_select(
        table="users_profile",
        select="email",
        filters={"user_id": state},
    )
    if not users_profile:
        raise HTTPException(status_code=404, detail="找不到使用者")

    teachers = await supabase_service.table_select(
        table="teachers",
        select="id",
        filters={"email": users_profile[0]["email"]},
    )
    if not teachers:
        raise HTTPException(status_code=404, detail="找不到對應的教師紀錄")

    teacher_id = teachers[0]["id"]
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
        raise HTTPException(status_code=404, detail="找不到教師紀錄")

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
