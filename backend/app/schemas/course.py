from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CourseBase(BaseModel):
    course_code: str = Field(..., min_length=1, max_length=50, description="課程代碼")
    course_name: str = Field(..., min_length=1, max_length=200, description="課程名稱")
    description: Optional[str] = Field(None, description="課程描述")
    duration_minutes: int = Field(60, ge=15, le=480, description="課程時長（分鐘）")
    is_active: bool = Field(True, description="是否啟用")


class CourseCreate(CourseBase):
    """建立課程的請求"""

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "course_code": "ENG-CONV-01",
                "course_name": "英語日常會話",
                "description": "適合初學者的日常英語會話課程",
                "duration_minutes": 60,
            }]
        }
    }


class CourseUpdate(BaseModel):
    """更新課程的請求"""
    course_code: Optional[str] = Field(None, min_length=1, max_length=50)
    course_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    is_active: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "course_name": "英語日常會話（進階）",
                "duration_minutes": 90,
            }]
        }
    }


class CourseResponse(CourseBase):
    """課程回應"""
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "course_code": "ENG-CONV-01",
                "course_name": "英語日常會話",
                "description": "適合初學者的日常英語會話課程",
                "duration_minutes": 60,
                "is_active": True,
                "created_at": "2026-03-15T10:00:00",
                "updated_at": "2026-03-15T10:00:00",
            }]
        }
    }


class CourseListResponse(BaseModel):
    """課程列表回應"""
    success: bool = True
    data: list[CourseResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
