from pydantic import BaseModel, Field
from typing import Optional
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
    # 關聯資料
    initiator_name: Optional[str] = None
    booking_no: Optional[str] = None
    approver_name: Optional[str] = None

    class Config:
        from_attributes = True


class LeaveRecordListResponse(BaseModel):
    success: bool = True
    data: list[LeaveRecordResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
