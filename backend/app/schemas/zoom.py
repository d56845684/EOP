from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime, date, time


# ============================================
# Zoom Account（帳號池）
# ============================================

class ZoomAccountCreate(BaseModel):
    """建立 Zoom 帳號"""
    account_name: str = Field(..., max_length=100, description="帳號名稱")
    zoom_account_id: str = Field(..., max_length=100, description="Zoom Account ID")
    zoom_client_id: str = Field(..., max_length=200, description="Zoom Client ID")
    zoom_client_secret: str = Field(..., max_length=200, description="Zoom Client Secret")
    zoom_user_email: Optional[str] = Field(None, max_length=255, description="Zoom 使用者 Email")
    is_active: bool = Field(True, description="是否啟用")
    notes: Optional[str] = Field(None, description="備註")


class ZoomAccountUpdate(BaseModel):
    """更新 Zoom 帳號"""
    account_name: Optional[str] = Field(None, max_length=100, description="帳號名稱")
    zoom_account_id: Optional[str] = Field(None, max_length=100, description="Zoom Account ID")
    zoom_client_id: Optional[str] = Field(None, max_length=200, description="Zoom Client ID")
    zoom_client_secret: Optional[str] = Field(None, max_length=200, description="Zoom Client Secret")
    zoom_user_email: Optional[str] = Field(None, max_length=255, description="Zoom 使用者 Email")
    is_active: Optional[bool] = Field(None, description="是否啟用")
    notes: Optional[str] = Field(None, description="備註")


class ZoomAccountResponse(BaseModel):
    """Zoom 帳號回應（不暴露 secret）"""
    id: str
    account_name: str
    zoom_account_id: str
    zoom_client_id: str
    zoom_user_email: Optional[str] = None
    is_active: bool = True
    daily_meeting_count: int = 0
    daily_count_reset_at: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ZoomAccountListResponse(BaseModel):
    """Zoom 帳號列表回應"""
    success: bool = True
    data: list[ZoomAccountResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0


# ============================================
# Zoom Meeting Log（會議紀錄）
# ============================================

class ZoomMeetingLogResponse(BaseModel):
    """Zoom 會議紀錄回應"""
    id: str
    booking_id: str
    zoom_account_id: Optional[str] = None
    teacher_id: Optional[str] = None
    zoom_meeting_id: str
    zoom_meeting_uuid: Optional[str] = None
    join_url: str
    start_url: Optional[str] = None
    passcode: Optional[str] = None
    meeting_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    meeting_status: str = "scheduled"
    recording_url: Optional[str] = None
    recording_download_url: Optional[str] = None
    recording_file_type: Optional[str] = None
    recording_file_size_bytes: Optional[int] = None
    recording_duration_seconds: Optional[int] = None
    recording_completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # enriched fields
    account_name: Optional[str] = None
    teacher_name: Optional[str] = None

    class Config:
        from_attributes = True


class ZoomMeetingLogListResponse(BaseModel):
    """Zoom 會議紀錄列表回應"""
    success: bool = True
    data: list[ZoomMeetingLogResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0


class ZoomMeetingCreateRequest(BaseModel):
    """手動建立 Zoom 會議"""
    booking_id: str = Field(..., description="預約 ID")


# ============================================
# Zoom OAuth（教師綁定）
# ============================================

class ZoomOAuthUrlResponse(BaseModel):
    """Zoom OAuth 授權 URL 回應"""
    success: bool = True
    authorize_url: str


class ZoomTeacherLinkStatus(BaseModel):
    """教師 Zoom 綁定狀態"""
    success: bool = True
    is_linked: bool = False
    zoom_email: Optional[str] = None
    zoom_user_id: Optional[str] = None
    linked_at: Optional[datetime] = None


# ============================================
# Zoom Webhook
# ============================================

class ZoomWebhookPayload(BaseModel):
    """Zoom Webhook payload"""
    event: str
    payload: dict = {}
    event_ts: Optional[int] = None
