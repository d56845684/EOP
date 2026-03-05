from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ========== Enums ==========

class AccessType(str, Enum):
    grant = "grant"
    revoke = "revoke"


class UserRoleEnum(str, Enum):
    admin = "admin"
    employee = "employee"
    teacher = "teacher"
    student = "student"


# ========== Roles CRUD ==========

class RoleCreate(BaseModel):
    """建立角色"""
    role: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z][a-z0-9_]*$', description="角色 key（英文小寫+底線）")
    name: str = Field(..., min_length=1, max_length=200, description="角色顯示名稱")
    description: Optional[str] = Field(None, description="角色描述")


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


# ========== Pages ==========

class PageCreate(BaseModel):
    """建立頁面"""
    key: str = Field(..., min_length=1, max_length=100, description="頁面 key（唯一）")
    name: str = Field(..., min_length=1, max_length=200, description="頁面名稱")
    description: Optional[str] = Field(None, description="描述")
    parent_key: Optional[str] = Field(None, max_length=100, description="父頁面 key")
    sort_order: int = Field(0, description="排序")
    is_active: bool = Field(True, description="是否啟用")


class PageUpdate(BaseModel):
    """更新頁面"""
    key: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    parent_key: Optional[str] = Field(None, max_length=100)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


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

    class Config:
        from_attributes = True


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
    role: str
    pages: List[PageResponse] = []


class RolePagesBatchSet(BaseModel):
    """批次設定角色頁面"""
    role: str = Field(..., description="角色 key")
    page_ids: List[str] = Field(..., description="頁面 ID 列表")


# ========== User Page Overrides ==========

class UserPageOverrideItem(BaseModel):
    """單一覆寫項目"""
    id: str
    page_id: str
    page_key: Optional[str] = None
    page_name: Optional[str] = None
    access_type: str
    created_at: Optional[datetime] = None


class UserPageOverridesResponse(BaseModel):
    """用戶覆寫回應"""
    success: bool = True
    user_id: str
    overrides: List[UserPageOverrideItem] = []


class UserPageOverrideEntry(BaseModel):
    """單一覆寫設定"""
    page_id: str = Field(..., description="頁面 ID")
    access_type: AccessType = Field(..., description="grant 或 revoke")


class UserPageOverridesBatchSet(BaseModel):
    """批次設定用戶覆寫"""
    overrides: List[UserPageOverrideEntry] = Field(..., description="覆寫列表")


# ========== Roles ==========

class RoleInfo(BaseModel):
    """角色資訊"""
    role: str
    name: str
    description: Optional[str] = None
    is_system: bool = False
    page_count: int = 0


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
