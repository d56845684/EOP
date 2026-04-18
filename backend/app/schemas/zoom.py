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
    account_tier: str = Field("basic", description="帳號等級 (basic/pro/business)")
    is_active: bool = Field(True, description="是否啟用")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "account_name": "EOP 教學帳號 A",
                "zoom_account_id": "AbC1dEf2GhI3jKl4",
                "zoom_client_id": "xYz5AbC6dEf7GhI8",
                "zoom_client_secret": "sEcReTkEy1234567890abcdef",
                "zoom_user_email": "zoom-a@eop-education.com",
                "account_tier": "pro",
            }]
        }
    }


class ZoomAccountUpdate(BaseModel):
    """更新 Zoom 帳號"""
    account_name: Optional[str] = Field(None, max_length=100, description="帳號名稱")
    zoom_account_id: Optional[str] = Field(None, max_length=100, description="Zoom Account ID")
    zoom_client_id: Optional[str] = Field(None, max_length=200, description="Zoom Client ID")
    zoom_client_secret: Optional[str] = Field(None, max_length=200, description="Zoom Client Secret")
    zoom_user_email: Optional[str] = Field(None, max_length=255, description="Zoom 使用者 Email")
    account_tier: Optional[str] = Field(None, description="帳號等級 (basic/pro/business)")
    is_active: Optional[bool] = Field(None, description="是否啟用")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "account_name": "EOP 教學帳號 A（已更新）",
                "account_tier": "business",
                "is_active": True,
                "notes": "升級為商業方案",
            }]
        }
    }


class ZoomAccountResponse(BaseModel):
    """Zoom 帳號回應（不暴露 secret）"""
    id: str
    account_name: str
    zoom_account_id: str
    zoom_client_id: str
    zoom_user_email: Optional[str] = None
    account_tier: str = "basic"
    is_active: bool = True
    daily_meeting_count: int = 0
    daily_count_reset_at: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "account_name": "EOP 教學帳號 A",
                "zoom_account_id": "AbC1dEf2GhI3jKl4",
                "zoom_client_id": "xYz5AbC6dEf7GhI8",
                "zoom_user_email": "zoom-a@eop-education.com",
                "account_tier": "pro",
                "is_active": True,
                "daily_meeting_count": 5,
                "daily_count_reset_at": "2026-04-14",
                "notes": "主要教學用帳號",
                "created_at": "2026-01-15T09:00:00",
                "created_by": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "updated_at": "2026-04-14T08:00:00",
            }]
        }
    }


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
    # Google Drive transfer
    recording_transfer_status: Optional[str] = None
    drive_file_id: Optional[str] = None
    drive_view_link: Optional[str] = None
    transferred_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # enriched fields
    account_name: Optional[str] = None
    teacher_name: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "booking_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "zoom_account_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "teacher_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
                "zoom_meeting_id": "98765432100",
                "zoom_meeting_uuid": "AbCdEfGhIjKlMnOp==",
                "join_url": "https://zoom.us/j/98765432100?pwd=abc123",
                "start_url": "https://zoom.us/s/98765432100?zak=xyz789",
                "passcode": "123456",
                "meeting_date": "2026-04-15",
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "meeting_status": "completed",
                "recording_url": "https://zoom.us/rec/share/abc123",
                "recording_download_url": "https://zoom.us/rec/download/abc123",
                "recording_file_type": "MP4",
                "recording_file_size_bytes": 524288000,
                "recording_duration_seconds": 3600,
                "recording_completed_at": "2026-04-15T15:05:00",
                "recording_transfer_status": "completed",
                "drive_file_id": "1AbCdEfGhIjKlMnOpQrStUvWxYz",
                "drive_view_link": "https://drive.google.com/file/d/1AbCdEfGh/view",
                "transferred_at": "2026-04-15T15:10:00",
                "created_at": "2026-04-15T13:55:00",
                "updated_at": "2026-04-15T15:10:00",
                "account_name": "EOP 教學帳號 A",
                "teacher_name": "陳老師",
            }]
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "booking_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            }]
        }
    }


# ============================================
# Internal: Lambda download token
# ============================================

class DownloadTokenRequest(BaseModel):
    """Lambda 請求下載 token"""
    meeting_id: str
    secret: str

class DownloadTokenResponse(BaseModel):
    """回傳 Zoom download URL + access token + Drive 設定"""
    download_url: str
    access_token: str
    # 會議資訊（檔案命名用）
    meeting_topic: Optional[str] = None             # 例: "[BK20260329003] 一般課程 Dennis / Test Teacher 2026-03-29 14:00"
    # Google Drive 上傳設定
    drive_mode: str = "sa"                          # 'sa' or 'oauth'
    drive_access_token: Optional[str] = None        # OAuth 模式用
    drive_folder_id: Optional[str] = None           # DB 設定的預設資料夾
    student_drive_folder_id: Optional[str] = None   # 學生專屬資料夾（正式學生）
    student_type: Optional[str] = None              # trial / formal（決定放哪個資料夾）

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "download_url": "https://zoom.us/rec/download/abc123def456",
                "access_token": "eyJhbGciOiJIUzI1NiJ9.eyJ...",
                "meeting_topic": "[BK20260415001] 英語初級會話 王小明 / 陳老師 2026-04-15 14:00",
                "drive_mode": "sa",
                "drive_folder_id": "1AbCdEfGhIjKlMnOpQrStUv",
                "student_drive_folder_id": "1WxYzAbCdEfGhIjKlMnOpQ",
                "student_type": "formal",
            }]
        }
    }


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


# ============================================
# Recording Callback（Lambda → Backend）
# ============================================

class RecordingCallbackRequest(BaseModel):
    """Lambda 錄影轉移完成回呼"""
    meeting_id: str
    status: str  # "completed" | "failed"
    drive_file_id: Optional[str] = None
    drive_view_link: Optional[str] = None
    error: Optional[str] = None
    secret: str
