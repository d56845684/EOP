from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ========== Enums ==========

class AccessType(str, Enum):
    grant = "grant"
    revoke = "revoke"


# ========== Roles CRUD ==========

class RoleCreate(BaseModel):
    """建立角色"""
    key: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z][a-z0-9_]*$', description="角色 key（英文小寫+底線）")
    name: str = Field(..., min_length=1, max_length=200, description="角色顯示名稱")
    description: Optional[str] = Field(None, description="角色描述")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "key": "senior_teacher",
                "name": "資深教師",
                "description": "具備進階排課與學生管理權限的教師角色",
            }]
        }
    }


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name": "資深教師（已更新）",
                "description": "更新角色描述與權限範圍",
            }]
        }
    }


# ========== Pages ==========

class PageCreate(BaseModel):
    """建立頁面"""
    key: str = Field(..., min_length=1, max_length=100, description="頁面 key（唯一）")
    name: str = Field(..., min_length=1, max_length=200, description="頁面名稱")
    description: Optional[str] = Field(None, description="描述")
    parent_key: Optional[str] = Field(None, max_length=100, description="父頁面 key")
    sort_order: int = Field(0, description="排序")
    is_active: bool = Field(True, description="是否啟用")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "key": "booking_management",
                "name": "預約管理",
                "description": "學生預約課程管理頁面",
                "parent_key": "dashboard",
                "sort_order": 3,
            }]
        }
    }


class PageUpdate(BaseModel):
    """更新頁面"""
    key: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    parent_key: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name": "預約管理（進階）",
                "sort_order": 5,
                "is_active": True,
            }]
        }
    }


class PageResponse(BaseModel):
    """頁面回應"""
    id: str
    key: str
    name: str
    description: Optional[str] = None
    parent_key: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "key": "booking_management",
                "name": "預約管理",
                "description": "學生預約課程管理頁面",
                "parent_key": "dashboard",
                "sort_order": 3,
                "is_active": True,
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-03-15T10:00:00",
            }]
        }
    }


class PageListResponse(BaseModel):
    """頁面列表回應"""
    success: bool = True
    data: List[PageResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 50
    total_pages: int = 0


# ========== Role Pages ==========

class RolePagesResponse(BaseModel):
    """角色頁面回應"""
    success: bool = True
    role_id: str
    pages: List[PageResponse] = []

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "success": True,
                "role_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "pages": [{
                    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "key": "booking_management",
                    "name": "預約管理",
                    "description": "學生預約課程管理頁面",
                    "parent_key": "dashboard",
                    "sort_order": 3,
                    "is_active": True,
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-03-15T10:00:00",
                }],
            }]
        }
    }


class RolePagesBatchSet(BaseModel):
    """批次設定角色頁面"""
    role_id: str = Field(..., description="角色 UUID")
    page_ids: List[str] = Field(..., description="頁面 ID 列表")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "role_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "page_ids": [
                    "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "c3d4e5f6-a7b8-9012-cdef-123456789012",
                ],
            }]
        }
    }


# ========== User Page Overrides ==========

class UserPageOverrideItem(BaseModel):
    """單一覆寫項目"""
    id: str
    page_id: str
    page_key: Optional[str] = None
    page_name: Optional[str] = None
    access_type: str
    created_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "page_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "page_key": "booking_management",
                "page_name": "預約管理",
                "access_type": "grant",
                "created_at": "2026-03-15T10:00:00",
            }]
        }
    }


class UserPageOverridesResponse(BaseModel):
    """用戶覆寫回應"""
    success: bool = True
    user_id: str
    overrides: List[UserPageOverrideItem] = []

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "success": True,
                "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "overrides": [{
                    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "page_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    "page_key": "booking_management",
                    "page_name": "預約管理",
                    "access_type": "grant",
                    "created_at": "2026-03-15T10:00:00",
                }],
            }]
        }
    }


class UserPageOverrideEntry(BaseModel):
    """單一覆寫設定"""
    page_id: str = Field(..., description="頁面 ID")
    access_type: AccessType = Field(..., description="grant 或 revoke")


class UserPageOverridesBatchSet(BaseModel):
    """批次設定用戶覆寫"""
    overrides: List[UserPageOverrideEntry] = Field(..., description="覆寫列表")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "overrides": [
                    {"page_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901", "access_type": "grant"},
                    {"page_id": "c3d4e5f6-a7b8-9012-cdef-123456789012", "access_type": "revoke"},
                ],
            }]
        }
    }


# ========== Roles ==========

class RoleInfo(BaseModel):
    """角色資訊"""
    id: str
    key: str
    name: str
    description: Optional[str] = None
    is_system: bool = False
    page_count: int = 0

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "key": "senior_teacher",
                "name": "資深教師",
                "description": "具備進階排課與學生管理權限的教師角色",
                "is_system": False,
                "page_count": 8,
            }]
        }
    }


class RoleListResponse(BaseModel):
    """角色列表回應"""
    success: bool = True
    data: List[RoleInfo] = []


# ========== My Permissions ==========

class MyPermissionsResponse(BaseModel):
    """當前用戶有效權限"""
    success: bool = True
    role: str
    page_keys: List[str] = []
    pages: List[PageResponse] = []

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "success": True,
                "role": "employee",
                "page_keys": ["dashboard", "booking_management", "student_management", "teacher_management"],
                "pages": [{
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "key": "dashboard",
                    "name": "儀表板",
                    "description": "系統總覽",
                    "parent_key": None,
                    "sort_order": 1,
                    "is_active": True,
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00",
                }],
            }]
        }
    }
