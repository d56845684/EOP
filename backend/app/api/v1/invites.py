from fastapi import APIRouter, HTTPException, Depends
from app.services.supabase_service import supabase_service
from app.services.invite_service import invite_service
from app.core.dependencies import require_staff, CurrentUser
from app.schemas.invite import (
    GenerateInviteRequest, GenerateInviteResponse,
    AcceptInviteRequest, AcceptInviteResponse,
)
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invites", tags=["邀請註冊"])


@router.post("/generate", response_model=GenerateInviteResponse)
async def generate_invite(
    data: GenerateInviteRequest,
    current_user: CurrentUser = Depends(require_staff),
):
    """產生邀請連結（僅限員工/管理員）"""
    try:
        table = "students" if data.entity_type == "student" else "teachers"

        # 1. 查 entity 存在且未刪除
        entities = await supabase_service.table_select(
            table=table,
            select="id,email,name,email_verified_at,is_deleted",
            filters={"id": data.entity_id, "is_deleted": "eq.false"},
        )
        if not entities:
            raise HTTPException(status_code=404, detail=f"{data.entity_type} 不存在")

        entity = entities[0]

        if not entity.get("email"):
            raise HTTPException(status_code=400, detail="該筆資料沒有 email，無法產生邀請")

        if entity.get("email_verified_at"):
            raise HTTPException(status_code=400, detail="此帳號已驗證，無需重新邀請")

        # 2. 檢查 email 未被 public.users 使用
        existing_users = await supabase_service.table_select(
            table="users",
            select="id",
            filters={"email": entity["email"]},
        )
        if existing_users:
            raise HTTPException(status_code=400, detail="此 email 已有登入帳號")

        # 3. 產生 token
        token, expires_at = await invite_service.generate_token(
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            email=entity["email"],
            name=entity["name"],
        )

        invite_url = f"{settings.FRONTEND_URL}/accept-invite?token={token}"

        return GenerateInviteResponse(invite_url=invite_url, expires_at=expires_at)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("產生邀請連結失敗")
        raise HTTPException(status_code=500, detail=f"產生邀請連結失敗: {str(e)}")


@router.post("/accept", response_model=AcceptInviteResponse)
async def accept_invite(data: AcceptInviteRequest):
    """接受邀請，建立帳號（無需登入）"""
    try:
        # 1. 消費 token
        token_data = await invite_service.consume_token(data.token)
        if not token_data:
            raise HTTPException(status_code=400, detail="邀請連結無效或已過期")

        entity_type = token_data["entity_type"]
        entity_id = token_data["entity_id"]
        email = token_data["email"]
        name = token_data["name"]
        table = "students" if entity_type == "student" else "teachers"

        # 2. 再次驗證 entity 存在、未刪除、未驗證
        entities = await supabase_service.table_select(
            table=table,
            select="id,email,email_verified_at,is_deleted",
            filters={"id": entity_id, "is_deleted": "eq.false"},
        )
        if not entities:
            raise HTTPException(status_code=400, detail="資料不存在或已被刪除")

        entity = entities[0]
        if entity.get("email_verified_at"):
            raise HTTPException(status_code=400, detail="此帳號已驗證")

        # 3. 建立 public.users 帳號
        metadata = {"full_name": name, "role": entity_type}
        auth_response = await supabase_service.sign_up(email, data.password, metadata)

        if not auth_response.user:
            raise HTTPException(status_code=500, detail="建立帳號失敗")

        user_id = auth_response.user.id

        # 4. INSERT user_profiles 帶入 student_id/teacher_id
        profile_data = {
            "id": user_id,
            "role": entity_type,
            "must_change_password": True,
        }
        if entity_type == "student":
            profile_data["student_id"] = entity_id
        else:
            profile_data["teacher_id"] = entity_id

        try:
            await supabase_service.table_insert(
                table="user_profiles",
                data=profile_data,
            )
        except Exception as profile_err:
            # rollback：刪除 public.users
            logger.error(f"建立 user_profiles 失敗，rollback user: {profile_err}")
            await supabase_service.admin_delete_user(user_id)
            raise HTTPException(status_code=500, detail="建立帳號失敗，請稍後再試")

        # 5. 設定 email_verified_at
        await supabase_service.table_update(
            table=table,
            data={"email_verified_at": "now()"},
            filters={"id": entity_id},
        )

        return AcceptInviteResponse(message="帳號建立成功，請使用 email 和密碼登入")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("接受邀請失敗")
        raise HTTPException(status_code=500, detail=f"建立帳號失敗: {str(e)}")
