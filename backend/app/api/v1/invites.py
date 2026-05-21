import uuid
from fastapi import APIRouter, HTTPException, Depends
from app.services.supabase_service import supabase_service
from app.services.invite_service import invite_service
from app.core.dependencies import require_staff, CurrentUser
from app.core.error_codes import ErrorCode
from app.core.exceptions import bad_request, forbidden, not_found, internal_error
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
        table_map = {"student": "students", "teacher": "teachers", "employee": "employees"}
        table = table_map[data.entity_type]

        # 1. 查 entity 存在且未刪除
        entities = await supabase_service.table_select(
            table=table,
            select="id,email,name,email_verified_at,is_deleted",
            filters={"id": data.entity_id, "is_deleted": "eq.false"},
        )
        if not entities:
            raise not_found("entity", ErrorCode.INVITE_ENTITY_NOT_FOUND)

        entity = entities[0]

        if not entity.get("email"):
            raise bad_request("該筆資料沒有 email，無法產生邀請", ErrorCode.INVITE_NO_EMAIL)

        if entity.get("email_verified_at"):
            raise bad_request("此帳號已驗證，無需重新邀請", ErrorCode.INVITE_ACCOUNT_VERIFIED_RESEND)

        # 2. 檢查 email 未被 public.users 使用
        existing_users = await supabase_service.table_select(
            table="users",
            select="id",
            filters={"email": entity["email"]},
        )
        if existing_users:
            raise bad_request("此 email 已有登入帳號", ErrorCode.INVITE_EMAIL_HAS_ACCOUNT)

        # 3. 產生 token（員工可附帶指定角色）
        token, expires_at = await invite_service.generate_token(
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            email=entity["email"],
            name=entity["name"],
            role_id=data.role_id if data.entity_type == "employee" else None,
        )

        invite_url = f"{settings.FRONTEND_URL}/accept-invite?token={token}"

        return GenerateInviteResponse(invite_url=invite_url, expires_at=expires_at)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("產生邀請連結失敗")
        raise internal_error(f"產生邀請連結失敗: {str(e)}", ErrorCode.INVITE_LINK_GENERATE_FAILED)


@router.post("/accept", response_model=AcceptInviteResponse)
async def accept_invite(data: AcceptInviteRequest):
    """接受邀請，建立帳號（無需登入）"""
    try:
        # 1. 消費 token
        token_data = await invite_service.consume_token(data.token)
        if not token_data:
            raise bad_request("邀請連結無效或已過期", ErrorCode.INVITE_LINK_INVALID)

        entity_type = token_data["entity_type"]
        entity_id = token_data["entity_id"]
        email = token_data["email"]
        name = token_data["name"]
        table_map = {"student": "students", "teacher": "teachers", "employee": "employees"}
        table = table_map.get(entity_type)
        if not table:
            raise bad_request(f"不支援的實體類型: {entity_type}", ErrorCode.INVITE_ENTITY_TYPE_INVALID)

        # 2. 再次驗證 entity 存在、未刪除、未驗證
        select_fields = "id,email,email_verified_at,is_deleted"
        if entity_type == "employee":
            select_fields += ",employee_type"
        entities = await supabase_service.table_select(
            table=table,
            select=select_fields,
            filters={"id": entity_id, "is_deleted": "eq.false"},
        )
        if not entities:
            raise bad_request("資料不存在或已被刪除", ErrorCode.INVITE_DATA_NOT_FOUND)

        entity = entities[0]
        if entity.get("email_verified_at"):
            raise bad_request("此帳號已驗證", ErrorCode.INVITE_ACCOUNT_VERIFIED)

        # 3. 建立 public.users 帳號
        metadata = {"full_name": name, "role": entity_type}
        auth_response = await supabase_service.sign_up(email, data.password, metadata)

        if not auth_response.user:
            raise internal_error("建立帳號失敗", ErrorCode.INVITE_CREATE_ACCOUNT_FAILED)

        user_id = auth_response.user.id

        # 4. INSERT user_profiles 帶入 student_id/teacher_id/employee_id
        #    角色決定：token 有指定 role_id → 直接用；否則從 employee_type 推導
        token_role_id = token_data.get("role_id")
        if token_role_id:
            assigned_role_id = token_role_id
        else:
            if entity_type == "employee":
                employee_type = entity.get("employee_type", "full_time")
                role_key = "admin" if employee_type == "admin" else "employee"
            else:
                role_key = entity_type
            role_row = await supabase_service.pool.fetchrow(
                "SELECT id FROM roles WHERE key = $1", role_key
            )
            if not role_row:
                raise internal_error(f"角色 '{role_key}' 不存在", ErrorCode.INVITE_ROLE_NOT_FOUND)
            assigned_role_id = str(role_row["id"])

        profile_data = {
            "id": user_id,
            "role_id": assigned_role_id,
            "must_change_password": True,
        }
        if entity_type == "student":
            profile_data["student_id"] = entity_id
        elif entity_type == "teacher":
            profile_data["teacher_id"] = entity_id
        elif entity_type == "employee":
            profile_data["employee_id"] = entity_id
            profile_data["employee_subtype"] = entity.get("employee_type", "full_time")

        try:
            await supabase_service.table_insert(
                table="user_profiles",
                data=profile_data,
            )
        except Exception as profile_err:
            # rollback：刪除 public.users
            logger.error(f"建立 user_profiles 失敗，rollback user: {profile_err}")
            await supabase_service.admin_delete_user(user_id)
            raise internal_error("建立帳號失敗，請稍後再試", ErrorCode.INVITE_CREATE_ACCOUNT_FAILED)

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
        raise internal_error(f"建立帳號失敗: {str(e)}", ErrorCode.INVITE_CREATE_ACCOUNT_FAILED)
