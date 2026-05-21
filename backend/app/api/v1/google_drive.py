"""
Google Drive OAuth — 管理員綁定個人 Drive 帳號
用於 Zoom 錄影上傳到個人 Google Drive（不需 Google Workspace）
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import RedirectResponse
from app.services.supabase_service import supabase_service
from app.services.google_service import google_drive_service
from app.core.dependencies import CurrentUser, require_staff, get_current_user
from app.core.error_codes import ErrorCode
from app.core.exceptions import bad_request, not_found, internal_error
from app.schemas.response import BaseResponse, DataResponse
from app.schemas.google_drive import GoogleDriveOAuthUrlResponse, GoogleDriveStatusResponse
from app.config import settings
from datetime import datetime, timezone, timedelta
import logging

router = APIRouter(prefix="/google-drive", tags=["Google Drive"])
logger = logging.getLogger(__name__)


# ── OAuth 端點 ──

@router.get("/oauth/authorize", response_model=GoogleDriveOAuthUrlResponse)
async def get_oauth_authorize_url(
    current_user: CurrentUser = Depends(require_staff),
):
    """取得 Google OAuth 授權 URL（僅限員工/管理員）"""
    if not settings.google_drive_oauth_configured:
        raise bad_request("Google Drive OAuth 尚未設定（缺少 GOOGLE_DRIVE_OAUTH_CLIENT_ID）", ErrorCode.GDRIVE_OAUTH_NO_CLIENT_ID)

    url = google_drive_service.get_oauth_authorize_url(state=current_user.user_id)
    return {"authorize_url": url}


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(""),
):
    """Google OAuth callback — 存 token 到 google_drive_config"""
    if not settings.google_drive_oauth_configured:
        raise bad_request("Google Drive OAuth 尚未設定", ErrorCode.GDRIVE_OAUTH_NOT_CONFIGURED)

    try:
        # 換 token
        token_data = await google_drive_service.exchange_code_for_token(code)
        if not token_data:
            raise internal_error("Google token exchange 失敗", ErrorCode.GDRIVE_TOKEN_EXCHANGE_FAILED)

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        if not refresh_token:
            raise bad_request("未取得 refresh_token，請確認 OAuth 設定含 access_type=offline", ErrorCode.GDRIVE_NO_REFRESH_TOKEN)

        # 取得使用者資訊
        user_info = await google_drive_service.get_user_info(access_token)
        google_email = user_info.get("email", "") if user_info else ""
        google_user_id = user_info.get("id", "") if user_info else ""

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        config_data = {
            "drive_mode": "oauth",
            "google_access_token": access_token,
            "google_refresh_token": refresh_token,
            "google_token_expires_at": expires_at.isoformat(),
            "google_email": google_email,
            "google_user_id": google_user_id,
            "linked_at": datetime.now(timezone.utc).isoformat(),
            "linked_by": state,  # user_id
            "is_active": True,
            "updated_at": "now()",
        }

        # Upsert：有就更新，沒有就建立
        existing = await supabase_service.table_select(
            table="google_drive_config",
            select="id",
            filters={"is_active": "eq.true"},
        )

        if existing:
            await supabase_service.table_update(
                table="google_drive_config",
                data=config_data,
                filters={"id": existing[0]["id"]},
            )
        else:
            await supabase_service.table_insert(
                table="google_drive_config",
                data=config_data,
            )

        logger.info(f"Google Drive OAuth 綁定成功: {google_email}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/zoom-accounts?google_drive=linked")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google Drive OAuth callback 失敗: {e}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/zoom-accounts?google_drive=error")


@router.get("/oauth/status", response_model=GoogleDriveStatusResponse)
async def get_drive_status(
    current_user: CurrentUser = Depends(get_current_user),
):
    """查詢 Google Drive 綁定狀態"""
    config = await google_drive_service.get_drive_config()

    if not config:
        return {
            "is_linked": False,
            "drive_mode": None,
            "google_email": None,
            "drive_folder_id": None,
            "linked_at": None,
        }

    return {
        "is_linked": True,
        "drive_mode": config.get("drive_mode"),
        "google_email": config.get("google_email"),
        "drive_folder_id": config.get("drive_folder_id"),
        "linked_at": config.get("linked_at"),
    }


@router.delete("/oauth/unlink", response_model=BaseResponse)
async def unlink_drive(
    current_user: CurrentUser = Depends(require_staff),
):
    """解除 Google Drive 綁定"""
    existing = await supabase_service.table_select(
        table="google_drive_config",
        select="id",
        filters={"is_active": "eq.true"},
    )
    if not existing:
        raise AppException(404, "未綁定 Google Drive", ErrorCode.GDRIVE_NOT_BOUND)

    await supabase_service.table_update(
        table="google_drive_config",
        data={
            "is_active": False,
            "google_access_token": None,
            "google_refresh_token": None,
            "google_token_expires_at": None,
            "updated_at": "now()",
        },
        filters={"id": existing[0]["id"]},
    )

    logger.info("Google Drive 綁定已解除")
    return BaseResponse(message="Google Drive 綁定已解除")


@router.put("/folder", response_model=BaseResponse)
async def update_drive_folder(
    folder_id: str = Query(..., description="Google Drive 資料夾 ID"),
    current_user: CurrentUser = Depends(require_staff),
):
    """設定上傳目標資料夾"""
    existing = await supabase_service.table_select(
        table="google_drive_config",
        select="id",
        filters={"is_active": "eq.true"},
    )
    if not existing:
        raise AppException(404, "請先綁定 Google Drive", ErrorCode.GDRIVE_BIND_REQUIRED)

    await supabase_service.table_update(
        table="google_drive_config",
        data={"drive_folder_id": folder_id, "updated_at": "now()"},
        filters={"id": existing[0]["id"]},
    )

    return BaseResponse(message=f"目標資料夾已設定: {folder_id}")
