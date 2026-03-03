from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class StudentTeacherPreferenceCreate(BaseModel):
    """建立學生教師偏好"""
    student_id: str = Field(..., description="學生 ID")
    course_id: Optional[str] = Field(None, description="課程 ID（NULL = 全域預設）")
    min_teacher_level: int = Field(1, description="最低可預約教師等級", ge=1)
    primary_teacher_id: Optional[str] = Field(None, description="主要教師 ID")


class StudentTeacherPreferenceUpdate(BaseModel):
    """更新學生教師偏好"""
    min_teacher_level: Optional[int] = Field(None, description="最低可預約教師等級", ge=1)
    primary_teacher_id: Optional[str] = Field(None, description="主要教師 ID")


class StudentTeacherPreferenceResponse(BaseModel):
    """學生教師偏好回應"""
    id: str
    student_id: str
    course_id: Optional[str] = None
    min_teacher_level: int = 1
    primary_teacher_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 關聯資料
    student_name: Optional[str] = None
    course_name: Optional[str] = None
    primary_teacher_name: Optional[str] = None

    class Config:
        from_attributes = True
