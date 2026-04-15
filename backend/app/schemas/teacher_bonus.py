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


class TeacherBonusUpdate(BaseModel):
    """更新教師獎金紀錄"""
    bonus_type: Optional[BonusType] = Field(None, description="獎金類型")
    amount: Optional[float] = Field(None, ge=0, description="金額")
    bonus_date: Optional[date] = Field(None, description="獎金日期")
    description: Optional[str] = Field(None, max_length=255, description="說明")
    related_student_id: Optional[str] = Field(None, description="關聯學生 ID")
    related_booking_id: Optional[str] = Field(None, description="關聯預約 ID")
    notes: Optional[str] = Field(None, description="備註")


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

    class Config:
        from_attributes = True


class TeacherBonusListResponse(BaseModel):
    """教師獎金紀錄列表回應"""
    success: bool = True
    data: list[TeacherBonusResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
