from fastapi import APIRouter, Request, Response, Depends, HTTPException
from app.services.auth_service import auth_service
from app.services.session_service import session_service
from app.services.supabase_service import supabase_service
from app.core.dependencies import get_current_user, CurrentUser
from app.schemas.auth import (
    LoginRequest, LoginResponse,
    LogoutRequest, RefreshResponse, PasswordResetRequest,
    PasswordUpdateRequest, UserInfo, TokenPair
)
from app.schemas.response import BaseResponse, DataResponse
from app.schemas.user import UserSessionInfo, UserSessionsResponse
from app.core.security import hash_session_id
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["認證"])

# 公開註冊已關閉，所有帳號建立請走 /api/v1/invites 流程


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response
):
    """用戶登入"""
    user_info, token_pair = await auth_service.login(
        email=data.email,
        password=data.password,
        request=request,
        response=response
    )
    
    return LoginResponse(
        user=user_info,
        tokens=token_pair
    )

@router.post("/logout", response_model=BaseResponse)
async def logout(
    request: Request,
    response: Response,
    data: LogoutRequest = LogoutRequest(),
    current_user: CurrentUser = Depends(get_current_user)
):
    """用戶登出"""
    await auth_service.logout(
        request=request,
        response=response,
        logout_all_devices=data.logout_all_devices
    )
    
    message = "已登出所有裝置" if data.logout_all_devices else "登出成功"
    return BaseResponse(message=message)

@router.post("/refresh", response_model=RefreshResponse)
async def refresh_tokens(
    request: Request,
    response: Response
):
    """刷新 Token"""
    token_pair = await auth_service.refresh_tokens(
        request=request,
        response=response
    )
    
    return RefreshResponse(tokens=token_pair)

@router.get("/me", response_model=DataResponse[UserInfo])
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得當前用戶資訊"""
    # 查詢 must_change_password
    profile_extra = await auth_service.get_profile_extra(current_user.user_id)

    return DataResponse(
        data=UserInfo(
            id=current_user.user_id,
            email=current_user.email,
            role=current_user.role,
            email_confirmed=True,
            employee_type=current_user.employee_type,
            permission_level=current_user.permission_level,
            must_change_password=profile_extra.get("must_change_password", False),
        )
    )

@router.get("/sessions", response_model=UserSessionsResponse)
async def get_user_sessions(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user)
):
    """取得用戶所有 Sessions"""
    sessions = await session_service.get_user_sessions(current_user.user_id)
    current_session_hash = hash_session_id(current_user.session_id)
    
    session_list = [
        UserSessionInfo(
            session_id=s.session_id[:16] + "...",  # 只顯示部分
            user_agent=s.user_agent,
            ip_address=s.ip_address,
            created_at=s.created_at,
            last_activity=s.last_activity,
            is_current=(s.session_id == current_session_hash)
        )
        for s in sessions
    ]
    
    return UserSessionsResponse(
        sessions=session_list,
        total=len(session_list)
    )

@router.delete("/sessions/{session_id}", response_model=BaseResponse)
async def revoke_session(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user)
):
    """撤銷特定 Session"""
    # 這裡的 session_id 是前端顯示的部分 ID，需要實際查找
    sessions = await session_service.get_user_sessions(current_user.user_id)
    
    for s in sessions:
        if s.session_id.startswith(session_id.replace("...", "")):
            await session_service.destroy_session(s.session_id)
            return BaseResponse(message="Session 已撤銷")
    
    return BaseResponse(success=False, message="Session 不存在")

@router.post("/password/reset", response_model=BaseResponse)
async def request_password_reset(data: PasswordResetRequest):
    """請求重設密碼"""
    try:
        await supabase_service.reset_password_email(
            email=data.email,
            redirect_url="https://your-app.com/reset-password"
        )
        return BaseResponse(message="重設密碼郵件已發送")
    except:
        # 為了安全，不透露郵箱是否存在
        return BaseResponse(message="如果該郵箱已註冊，您將收到重設密碼郵件")


@router.post("/password/change", response_model=BaseResponse)
async def change_password(
    data: PasswordUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user)
):
    """變更密碼（首次登入或主動變更）

    需要提供當前密碼和新密碼。
    若 must_change_password 為 True，變更成功後會自動設為 False。
    """
    # 1. 驗證 current_password（透過 sign_in 驗證）
    try:
        await supabase_service.sign_in_with_password(
            email=current_user.email,
            password=data.current_password
        )
    except Exception:
        raise HTTPException(status_code=400, detail="當前密碼錯誤")

    # 2. 更新密碼
    try:
        result = await supabase_service.admin_update_user(
            user_id=current_user.user_id,
            attributes={"password": data.new_password}
        )
        if not result:
            raise HTTPException(status_code=500, detail="密碼更新失敗")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"密碼更新失敗: {str(e)}")

    # 3. 將 must_change_password 設為 False
    try:
        await supabase_service.table_update(
            table="user_profiles",
            data={"must_change_password": False},
            filters={"id": current_user.user_id},
            use_service_key=True
        )
    except Exception:
        pass  # 密碼已更新成功，此步驟失敗不影響

    return BaseResponse(message="密碼變更成功")
