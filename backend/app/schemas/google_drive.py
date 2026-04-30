from pydantic import BaseModel
from typing import Optional


class GoogleDriveOAuthUrlResponse(BaseModel):
    """Google Drive OAuth 授權 URL 回應"""
    success: bool = True
    authorize_url: str


class GoogleDriveStatusResponse(BaseModel):
    """Google Drive 綁定狀態回應"""
    success: bool = True
    is_linked: bool = False
    drive_mode: Optional[str] = None
    google_email: Optional[str] = None
    drive_folder_id: Optional[str] = None
    linked_at: Optional[str] = None
