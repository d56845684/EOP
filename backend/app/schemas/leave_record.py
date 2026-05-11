from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime, date, time
from enum import Enum


class LeaveStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class LeaveInitiatorType(str, Enum):
    student = "student"
    teacher = "teacher"


class LeaveRecordCreate(BaseModel):
    booking_id: str = Field(..., description="預約 ID")
    reason: str = Field(..., min_length=1, description="請假原因")
    initiator_type: Optional[Literal["student", "teacher"]] = Field(
        None,
        description="代申請對象（僅員工呼叫時必填，學生 / 老師呼叫時自動由角色推斷，忽略此欄位）",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "booking_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "reason": "身體不適，需要請假一次",
                "initiator_type": "student",
            }]
        }
    }


class LeaveRecordReject(BaseModel):
    rejection_reason: str = Field(..., min_length=1, description="駁回原因")


class LeaveRecordResponse(BaseModel):
    id: str
    leave_no: str
    initiator_type: LeaveInitiatorType
    initiator_student_id: Optional[str] = None
    initiator_teacher_id: Optional[str] = None
    booking_id: Optional[str] = None
    leave_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    reason: str
    leave_status: LeaveStatus = LeaveStatus.pending
    approver_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 請假類型 + 扣堂
    leave_type: Optional[str] = None  # normal / emergency
    deduct_lesson: bool = False
    emergency_quota: Optional[int] = None  # 該合約緊急請假總額度
    used_emergency_count: Optional[int] = None  # 已用緊急請假次數
    # 關聯資料
    initiator_name: Optional[str] = None
    booking_no: Optional[str] = None
    approver_name: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "leave_no": "LV20260410001",
                "initiator_type": "student",
                "initiator_student_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "initiator_teacher_id": None,
                "booking_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "leave_date": "2026-04-15",
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "reason": "身體不適，需要請假一次",
                "leave_status": "approved",
                "approver_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
                "approved_at": "2026-04-14T10:30:00",
                "rejection_reason": None,
                "created_at": "2026-04-14T09:00:00",
                "updated_at": "2026-04-14T10:30:00",
                "leave_type": "normal",
                "deduct_lesson": False,
                "emergency_quota": 3,
                "used_emergency_count": 0,
                "initiator_name": "王小明",
                "booking_no": "BK20260415001",
                "approver_name": "張主任",
            }]
        }
    }


class LeaveRecordListResponse(BaseModel):
    success: bool = True
    data: list[LeaveRecordResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
