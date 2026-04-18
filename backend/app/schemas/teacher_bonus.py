from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class BonusType(str, Enum):
    trial_completed = "trial_completed"
    trial_to_formal = "trial_to_formal"
    performance = "performance"
    substitute = "substitute"
    referral = "referral"
    other = "other"


BONUS_TYPE_LABELS = {
    "trial_completed": "試上完成",
    "trial_to_formal": "試上轉正",
    "performance": "績效獎金",
    "substitute": "代課獎金",
    "referral": "推薦獎金",
    "other": "其他",
}


class TeacherBonusCreate(BaseModel):
    """建立教師獎金紀錄"""
    teacher_id: str = Field(..., description="教師 ID")
    bonus_type: BonusType = Field(..., description="獎金類型")
    amount: float = Field(..., ge=0, description="金額")
    bonus_date: Optional[date] = Field(None, description="獎金日期（預設今天）")
    description: Optional[str] = Field(None, max_length=255, description="說明")
    related_student_id: Optional[str] = Field(None, description="關聯學生 ID")
    related_booking_id: Optional[str] = Field(None, description="關聯預約 ID")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "teacher_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "bonus_type": "trial_to_formal",
                "amount": 500.0,
                "bonus_date": "2026-04-10",
                "description": "學生王小明試上轉正獎金",
            }]
        }
    }


class TeacherBonusUpdate(BaseModel):
    """更新教師獎金紀錄"""
    bonus_type: Optional[BonusType] = Field(None, description="獎金類型")
    amount: Optional[float] = Field(None, ge=0, description="金額")
    bonus_date: Optional[date] = Field(None, description="獎金日期")
    description: Optional[str] = Field(None, max_length=255, description="說明")
    related_student_id: Optional[str] = Field(None, description="關聯學生 ID")
    related_booking_id: Optional[str] = Field(None, description="關聯預約 ID")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "amount": 600.0,
                "description": "調整獎金金額",
                "notes": "主管核准調整",
            }]
        }
    }


class TeacherBonusResponse(BaseModel):
    """教師獎金紀錄回應"""
    id: str
    teacher_id: str
    bonus_type: str
    amount: float
    bonus_date: Optional[date] = None
    description: Optional[str] = None
    related_student_id: Optional[str] = None
    related_booking_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    # enriched fields
    teacher_name: Optional[str] = None
    student_name: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "teacher_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "bonus_type": "trial_to_formal",
                "amount": 500.0,
                "bonus_date": "2026-04-10",
                "description": "學生王小明試上轉正獎金",
                "related_student_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "related_booking_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
                "notes": "已確認轉正",
                "created_at": "2026-04-10T09:00:00",
                "created_by": "e5f6a7b8-c9d0-1234-efab-345678901234",
                "updated_at": "2026-04-10T09:00:00",
                "teacher_name": "陳老師",
                "student_name": "王小明",
            }]
        }
    }


class TeacherBonusListResponse(BaseModel):
    """教師獎金紀錄列表回應"""
    success: bool = True
    data: list[TeacherBonusResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
