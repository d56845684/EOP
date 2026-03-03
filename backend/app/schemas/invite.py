from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class GenerateInviteRequest(BaseModel):
    """產生邀請連結請求"""
    entity_type: Literal["student", "teacher"] = Field(..., description="實體類型")
    entity_id: str = Field(..., description="實體 ID")


class GenerateInviteResponse(BaseModel):
    """產生邀請連結回應"""
    invite_url: str
    expires_at: datetime


class AcceptInviteRequest(BaseModel):
    """接受邀請請求"""
    token: str = Field(..., description="邀請 Token")
    password: str = Field(..., min_length=6, description="密碼（至少 6 碼）")


class AcceptInviteResponse(BaseModel):
    """接受邀請回應"""
    success: bool = True
    message: str = "帳號建立成功"


class InviteTokenData(BaseModel):
    """邀請 Token 資料（存在 Redis）"""
    entity_type: Literal["student", "teacher"]
    entity_id: str
    email: str
    name: str
    created_at: str
