from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class TeacherDetailType(str, Enum):
    qualification = "qualification"
    certificate = "certificate"
    video = "video"
    experience = "experience"


class TeacherDetailCreate(BaseModel):
    """建立教師明細"""
    teacher_id: str = Field(..., description="教師 ID")
    detail_type: TeacherDetailType = Field(..., description="明細類型")
    content: Optional[str] = Field(None, description="內容")
    issue_date: Optional[date] = Field(None, description="發證日期")
    expiry_date: Optional[date] = Field(None, description="到期日期")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "teacher_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "detail_type": "certificate",
                "content": "TESOL 國際英語教學證照",
                "issue_date": "2024-06-15",
                "expiry_date": "2027-06-15",
            }]
        }
    }


class TeacherDetailUpdate(BaseModel):
    """更新教師明細"""
    content: Optional[str] = Field(None, description="內容")
    issue_date: Optional[date] = Field(None, description="發證日期")
    expiry_date: Optional[date] = Field(None, description="到期日期")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "content": "TESOL 國際英語教學證照（進階）",
                "expiry_date": "2028-06-15",
            }]
        }
    }


class TeacherDetailResponse(BaseModel):
    """教師明細回應"""
    id: str
    teacher_id: str
    detail_type: str
    content: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeacherDetailListResponse(BaseModel):
    """教師明細列表回應"""
    success: bool = True
    data: list[TeacherDetailResponse] = []
