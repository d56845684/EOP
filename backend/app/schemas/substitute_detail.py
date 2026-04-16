from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SubstituteDetailCreate(BaseModel):
    booking_id: str = Field(..., description="預約 ID")
    substitute_teacher_id: str = Field(..., description="代課教師 ID")
    substitute_contract_id: str = Field(..., description="代課教師合約 ID")
    reason: Optional[str] = Field(None, description="代課原因")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "booking_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "substitute_teacher_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "substitute_contract_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "reason": "原教師臨時請假，安排代課",
            }]
        }
    }


class SubstituteDetailResponse(BaseModel):
    id: str
    booking_id: str
    substitute_teacher_id: str
    substitute_contract_id: str
    substitute_hourly_rate: Optional[float] = None
    reason: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 關聯資料
    substitute_teacher_name: Optional[str] = None
    booking_no: Optional[str] = None
    original_teacher_name: Optional[str] = None

    class Config:
        from_attributes = True


class SubstituteDetailListResponse(BaseModel):
    success: bool = True
    data: list[SubstituteDetailResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
