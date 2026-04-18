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

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "success": True,
                "message": "操作成功",
                "upload_url": "https://s3.amazonaws.com/eop-bucket/upload?X-Amz-Signature=abc123",
                "storage_path": "contracts/SC20260101001.pdf",
                "content_type": "application/pdf",
                "max_size_bytes": 10485760,
            }]
        }
    }

class DownloadUrlResponse(BaseResponse):
    """Signed download URL 回應"""
    download_url: str
    file_name: str = ""

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "success": True,
                "message": "操作成功",
                "download_url": "https://s3.amazonaws.com/eop-bucket/contracts/SC20260101001.pdf?X-Amz-Signature=abc123",
                "file_name": "SC20260101001.pdf",
            }]
        }
    }


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


# ============================================================
# 共用：下拉選單 Option 型別
# ============================================================

class StudentOption(BaseModel):
    """學生下拉選項"""
    id: str
    student_no: str
    name: str
    student_type: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "student_no": "S001",
                "name": "王小明",
                "student_type": "formal",
            }]
        }
    }

class TeacherOption(BaseModel):
    """教師下拉選項"""
    id: str
    teacher_no: str
    name: str
    teacher_level: Optional[int] = None
    is_preferred: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "teacher_no": "T001",
                "name": "陳老師",
                "teacher_level": 3,
                "is_preferred": True,
            }]
        }
    }

class CourseOption(BaseModel):
    """課程下拉選項"""
    id: str
    course_code: Optional[str] = None
    course_name: str

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "course_code": "ENG-A1",
                "course_name": "英語初級會話",
            }]
        }
    }

class ContractOption(BaseModel):
    """合約下拉選項"""
    id: str
    contract_no: str
    remaining_lessons: Optional[int] = None
    course_id: Optional[str] = None
    course_ids: Optional[List[str]] = None
    course_name: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "contract_no": "SC20260101001",
                "remaining_lessons": 18,
                "course_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "course_ids": ["b2c3d4e5-f6a7-8901-bcde-f12345678901"],
                "course_name": "英語初級會話",
                "created_at": "2026-03-15T10:00:00",
            }]
        }
    }

class RoleOption(BaseModel):
    """角色下拉選項"""
    id: str
    key: str
    name: str

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "key": "senior_teacher",
                "name": "資深教師",
            }]
        }
    }

class SlotOption(BaseModel):
    """教師時段下拉選項"""
    id: str
    slot_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    teacher_contract_id: Optional[str] = None
    is_booked: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "slot_date": "2026-04-15",
                "start_time": "14:00",
                "end_time": "15:00",
                "teacher_contract_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "is_booked": False,
            }]
        }
    }