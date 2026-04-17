from pydantic import BaseModel
from typing import Optional, Any, Generic, TypeVar, List

T = TypeVar("T")

class BaseResponse(BaseModel):
    success: bool = True
    message: str = "操作成功"
    
class DataResponse(BaseResponse, Generic[T]):
    data: Optional[T] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    details: Optional[Any] = None

class PaginatedResponse(BaseResponse, Generic[T]):
    data: List[T] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0


# ============================================================
# 共用：檔案上傳/下載
# ============================================================

class UploadUrlResponse(BaseResponse):
    """Presigned upload URL 回應"""
    upload_url: str
    storage_path: str
    content_type: str
    max_size_bytes: int = 10485760  # 10MB

class DownloadUrlResponse(BaseResponse):
    """Signed download URL 回應"""
    download_url: str
    file_name: str = ""


# ============================================================
# 共用：告警
# ============================================================

class AlertListResponse(BaseResponse):
    """告警列表"""
    data: List[Any] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
    unread_count: int = 0

class UnreadCountResponse(BaseResponse):
    """未讀數量"""
    count: int = 0