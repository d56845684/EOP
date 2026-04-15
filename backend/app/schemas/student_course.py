from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StudentCourseCreate(BaseModel):
    """建立學生選課"""
    student_id: str = Field(..., description="學生 ID")
    course_id: str = Field(..., description="課程 ID")


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

    class Config:
        from_attributes = True


class StudentCourseListResponse(BaseModel):
    """學生選課列表回應"""
    success: bool = True
    data: list[StudentCourseResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
