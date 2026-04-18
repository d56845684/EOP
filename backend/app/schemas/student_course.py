from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StudentCourseCreate(BaseModel):
    """建立學生選課"""
    student_id: str = Field(..., description="學生 ID")
    course_id: str = Field(..., description="課程 ID")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "student_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "course_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            }]
        }
    }


class StudentCourseResponse(BaseModel):
    """學生選課回應"""
    id: str
    student_id: str
    course_id: str
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    student_name: Optional[str] = None
    enrolled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "student_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "course_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "course_code": "ENG-A1",
                "course_name": "英語初級會話",
                "student_name": "王小明",
                "enrolled_at": "2026-03-01T10:00:00",
                "created_at": "2026-03-01T10:00:00",
            }]
        }
    }


class StudentCourseListResponse(BaseModel):
    """學生選課列表回應"""
    success: bool = True
    data: list[StudentCourseResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
