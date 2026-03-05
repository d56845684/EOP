from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserProfile(BaseModel):
    id: str
    email: str
    role: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

class UserSessionInfo(BaseModel):
    session_id: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: str
    last_activity: str
    is_current: bool = False

class UserSessionsResponse(BaseModel):
    sessions: List[UserSessionInfo]
    total: int


# ========== 帳號管理 ==========

class AccountInfo(BaseModel):
    """帳號資訊（含 email、名稱）"""
    id: str
    email: str
    name: Optional[str] = None
    role: str
    employee_subtype: Optional[str] = None
    is_active: bool = True
    is_protected: bool = False
    created_at: Optional[datetime] = None

class AccountUpdate(BaseModel):
    """帳號更新"""
    role: Optional[str] = None
    employee_subtype: Optional[str] = None
    is_active: Optional[bool] = None