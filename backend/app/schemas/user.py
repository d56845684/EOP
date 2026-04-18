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

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "email": "teacher@eop-education.com",
                "role": "teacher",
                "name": "陳老師",
                "avatar_url": "https://s3.amazonaws.com/eop/avatars/teacher001.jpg",
                "is_active": True,
                "created_at": "2026-01-15T09:00:00",
            }]
        }
    }

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
    role_id: Optional[str] = None
    employee_subtype: Optional[str] = None
    is_active: bool = True
    is_protected: bool = False
    created_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "email": "employee@eop-education.com",
                "name": "張主任",
                "role": "employee",
                "role_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "employee_subtype": "full_time",
                "is_active": True,
                "is_protected": False,
                "created_at": "2026-01-10T08:00:00",
            }]
        }
    }

class AccountUpdate(BaseModel):
    """帳號更新"""
    role_id: Optional[str] = None
    employee_subtype: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "role_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "employee_subtype": "full_time",
                "is_active": True,
            }]
        }
    }