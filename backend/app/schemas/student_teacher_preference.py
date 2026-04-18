from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StudentTeacherPreferenceCreate(BaseModel):
    """建立學生教師偏好（指定教師模式用 primary_teacher_ids，等級模式用 min_teacher_level）"""
    student_id: str = Field(..., description="學生 ID")
    course_id: Optional[str] = Field(None, description="課程 ID（NULL = 全域預設）")
    min_teacher_level: Optional[int] = Field(None, description="最高可預約教師等級", ge=1)
    primary_teacher_ids: Optional[List[str]] = Field(None, description="主要教師 ID 列表（1 筆走單筆，多筆走批次）")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "student_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "course_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "min_teacher_level": 3,
                "primary_teacher_ids": [
                    "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    "d4e5f6a7-b8c9-0123-defa-234567890123",
                ],
            }]
        }
    }


class StudentTeacherPreferenceUpdate(BaseModel):
    """更新學生教師偏好"""
    min_teacher_level: Optional[int] = Field(None, description="最低可預約教師等級", ge=1)
    primary_teacher_id: Optional[str] = Field(None, description="主要教師 ID")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "min_teacher_level": 2,
                "primary_teacher_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
            }]
        }
    }


class StudentTeacherPreferenceResponse(BaseModel):
    """學生教師偏好回應"""
    id: str
    student_id: str
    course_id: Optional[str] = None
    min_teacher_level: Optional[int] = None
    primary_teacher_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 關聯資料
    student_name: Optional[str] = None
    course_name: Optional[str] = None
    primary_teacher_name: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "student_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "course_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "min_teacher_level": 3,
                "primary_teacher_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
                "created_at": "2026-03-15T10:00:00",
                "updated_at": "2026-03-15T10:00:00",
                "student_name": "王小明",
                "course_name": "英語初級會話",
                "primary_teacher_name": "陳老師",
            }]
        }
    }
