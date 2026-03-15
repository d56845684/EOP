from fastapi import Depends, Request
from typing import Optional
from app.services.session_service import session_service
from app.services.permission_service import permission_service
from app.core.security import get_token_from_request, decode_token, TokenType
from app.core.exceptions import (
    AuthException, InvalidTokenException,
    SessionExpiredException, PermissionDeniedException
)
from app.models.session import SessionData


class CurrentUser:
    """當前用戶資訊"""

    def __init__(
        self,
        user_id: str,
        email: str,
        role: str,
        role_id: Optional[str] = None,
        session_id: Optional[str] = None,
        session_data: Optional[SessionData] = None,
        employee_type: Optional[str] = None,
        permission_level: int = 0,
        is_service_account: bool = False,
        student_id: Optional[str] = None,
        teacher_id: Optional[str] = None,
        employee_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.role_id = role_id
        self.session_id = session_id
        self.session_data = session_data
        self.employee_type = employee_type
        self.permission_level = permission_level
        self.is_service_account = is_service_account
        self.student_id = student_id
        self.teacher_id = teacher_id
        self.employee_id = employee_id

    def is_admin(self) -> bool:
        """檢查是否為管理員（權限等級 100）"""
        return self.permission_level >= 100

    def is_staff(self) -> bool:
        """檢查是否為員工（含管理員）"""
        return self.employee_id is not None

    def is_teacher(self) -> bool:
        """檢查是否為教師"""
        return self.teacher_id is not None

    def is_student(self) -> bool:
        """檢查是否為學生"""
        return self.student_id is not None

    def has_permission(self, required_level: int) -> bool:
        """檢查是否有足夠的權限等級"""
        return self.permission_level >= required_level

    def is_full_time_or_above(self) -> bool:
        """檢查是否為正式員工以上（等級 >= 30）"""
        return self.permission_level >= 30

    def is_part_time_or_above(self) -> bool:
        """檢查是否為兼職員工以上（等級 >= 20）"""
        return self.permission_level >= 20

    def is_intern_or_above(self) -> bool:
        """檢查是否為工讀生以上（等級 >= 10）"""
        return self.permission_level >= 10

    def can_manage(self, target_employee_type: Optional[str]) -> bool:
        """檢查是否可以管理指定類型的員工"""
        return permission_service.can_manage(self.employee_type, target_employee_type)


async def get_current_user(request: Request) -> CurrentUser:
    """取得當前已認證的用戶"""
    # Service Account：由 middleware 驗證 API Key 後標記
    if getattr(request.state, "is_service_account", False):
        return CurrentUser(
            user_id="service-account",
            email="service@system.internal",
            role="employee",
            is_service_account=True,
            employee_type="admin",
            permission_level=100,
            employee_id="service-account",
        )

    # 1. 取得 Token
    token = get_token_from_request(request)
    if not token:
        raise AuthException("未提供認證資訊")

    # 2. 複用 middleware 已驗證的結果（避免重複黑名單檢查 + JWT 解碼）
    payload = getattr(request.state, "token_payload", None)
    if not payload:
        # Fallback：middleware 未處理到的路徑
        if await session_service.is_token_blacklisted(token):
            raise InvalidTokenException()
        payload = decode_token(token)

    if not payload:
        raise InvalidTokenException()

    if payload.get("type") != TokenType.ACCESS:
        raise InvalidTokenException()

    # 3. 取得 Session 並更新活動時間（合併為單次操作，含 30 秒節流）
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise SessionExpiredException()

    session_data = await session_service.get_session_and_touch(session_id)
    if not session_data:
        raise SessionExpiredException()

    # 4. 驗證 Session 與 Token 匹配
    if session_data.user_id != payload.get("sub"):
        raise InvalidTokenException()

    # 7. 取得權限等級（從 token 或查詢）
    user_id = payload.get("sub")
    employee_type = payload.get("employee_type")
    permission_level = payload.get("permission_level", 0)

    # 取出 entity IDs（從 JWT payload）
    student_id = payload.get("student_id")
    teacher_id = payload.get("teacher_id")
    employee_id = payload.get("employee_id")

    # Fallback：舊 token 沒有 entity IDs，從 DB 查詢
    if student_id is None and teacher_id is None and employee_id is None:
        from app.services.auth_service import auth_service
        identity = await auth_service._get_user_identity(user_id)
        student_id = identity["student_id"]
        teacher_id = identity["teacher_id"]
        employee_id = identity["employee_id"]

    # 如果 token 中沒有權限資訊，從服務查詢
    if permission_level == 0 and employee_id is not None:
        permission_level = await permission_service.get_user_permission_level(user_id)
        if not employee_type:
            employee_type = await permission_service.get_user_employee_type(user_id)

    return CurrentUser(
        user_id=user_id,
        email=payload.get("email", ""),
        role=payload.get("role", "student"),
        role_id=payload.get("role_id"),
        session_id=session_id,
        session_data=session_data,
        employee_type=employee_type,
        permission_level=permission_level,
        student_id=student_id,
        teacher_id=teacher_id,
        employee_id=employee_id,
    )


async def get_optional_user(request: Request) -> Optional[CurrentUser]:
    """取得當前用戶（可選，未登入返回 None）"""
    try:
        return await get_current_user(request)
    except:
        return None


def require_role(*allowed_roles: str):
    """角色權限檢查裝飾器（使用 entity ID 判斷）"""
    async def role_checker(
        current_user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        has_role = False
        for role in allowed_roles:
            if role in ("admin", "employee") and current_user.employee_id is not None:
                has_role = True
                break
            if role == "teacher" and current_user.teacher_id is not None:
                has_role = True
                break
            if role == "student" and current_user.student_id is not None:
                has_role = True
                break
        if not has_role:
            raise PermissionDeniedException(
                f"需要以下角色之一: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


def require_permission_level(min_level: int):
    """
    權限等級檢查裝飾器

    Args:
        min_level: 所需的最低權限等級
            - 10: 工讀生
            - 20: 兼職員工
            - 30: 正式員工
            - 100: 管理員
    """
    async def permission_checker(
        current_user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        # 非員工角色無權限等級
        if current_user.employee_id is None:
            raise PermissionDeniedException("此操作需要員工權限")

        if current_user.permission_level < min_level:
            level_name = permission_service.get_level_name(min_level)
            raise PermissionDeniedException(
                f"權限不足，需要 {level_name} 以上權限"
            )
        return current_user
    return permission_checker


# 預定義的角色依賴
require_admin = require_role("admin")
require_staff = require_role("admin", "employee")
require_teacher = require_role("admin", "employee", "teacher")
require_authenticated = get_current_user

# 預定義的權限等級依賴
require_intern_level = require_permission_level(10)      # 工讀生以上
require_part_time_level = require_permission_level(20)   # 兼職員工以上
require_full_time_level = require_permission_level(30)   # 正式員工以上
require_admin_level = require_permission_level(100)      # 管理員


def require_page_permission(page_key: str):
    """
    統一的頁面權限檢查。

    所有角色（含 student/teacher）都透過 role → role_pages → page key 控制。
    - Service account: 直接通過
    - 其他: 檢查 page key（含 user overrides）
    """
    async def checker(
        current_user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        # service account bypass
        if current_user.is_service_account:
            return current_user

        # 所有角色都走 page key 檢查
        keys = await permission_service.get_effective_page_keys(
            current_user.role_id, current_user.user_id
        )
        if page_key not in keys:
            raise PermissionDeniedException(f"缺少頁面權限: {page_key}")

        return current_user
    return checker


async def get_user_employee_id(user_id: str) -> Optional[str]:
    """取得用戶關聯的員工 ID（用於 created_by / deleted_by 欄位）"""
    from app.services.supabase_service import supabase_service
    profile = await supabase_service.table_select(
        table="user_profiles",
        select="employee_id",
        filters={"id": user_id},
    )
    if profile and profile[0].get("employee_id"):
        return profile[0]["employee_id"]
    return None


async def get_user_student_id(user_id: str) -> Optional[str]:
    """取得用戶關聯的學生 ID"""
    from app.services.supabase_service import supabase_service
    profile = await supabase_service.table_select(
        table="user_profiles",
        select="student_id",
        filters={"id": user_id},
    )
    if profile and profile[0].get("student_id"):
        return profile[0]["student_id"]
    return None


async def get_user_teacher_id(user_id: str) -> Optional[str]:
    """取得用戶關聯的教師 ID"""
    from app.services.supabase_service import supabase_service
    profile = await supabase_service.table_select(
        table="user_profiles",
        select="teacher_id",
        filters={"id": user_id},
    )
    if profile and profile[0].get("teacher_id"):
        return profile[0]["teacher_id"]
    return None
