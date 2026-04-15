from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class TeacherBasicInfo(BaseModel):
    id: str
    teacher_no: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    teacher_level: Optional[int] = None
    is_active: bool = True
    email_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class TeacherAccountInfo(BaseModel):
    has_account: bool = False
    is_active: Optional[bool] = None
    role: Optional[str] = None


class TeacherLineBinding(BaseModel):
    bound: bool = False
    line_display_name: Optional[str] = None
    line_picture_url: Optional[str] = None
    binding_status: Optional[str] = None


class TeacherContractSummary(BaseModel):
    id: str
    contract_no: str
    contract_status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    employment_type: Optional[str] = None
    notes: Optional[str] = None
    addendum_count: int = 0


class TeacherBookingSummary(BaseModel):
    id: str
    booking_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    booking_status: str = "pending"
    booking_type: Optional[str] = None
    student_name: Optional[str] = None
    course_name: Optional[str] = None


class TeacherBonusSummary(BaseModel):
    id: str
    bonus_type: Optional[str] = None
    amount: Optional[float] = None
    bonus_date: Optional[date] = None
    description: Optional[str] = None
    student_name: Optional[str] = None


class TeacherWorkScheduleSummary(BaseModel):
    id: str
    weekday: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    notes: Optional[str] = None


class TeacherStats(BaseModel):
    total_bookings: int = 0
    completed_bookings: int = 0
    cancelled_bookings: int = 0
    pending_bookings: int = 0
    upcoming_bookings: int = 0
    total_contracts: int = 0
    active_contracts: int = 0
    total_bonus_amount: float = 0
    total_bonus_count: int = 0
    total_students_taught: int = 0


class TeacherViewResponse(BaseModel):
    teacher: TeacherBasicInfo
    account: TeacherAccountInfo
    line_binding: TeacherLineBinding
    contracts: list[TeacherContractSummary] = []
    bookings_recent: list[TeacherBookingSummary] = []
    bonus_records_recent: list[TeacherBonusSummary] = []
    work_schedules: list[TeacherWorkScheduleSummary] = []
    stats: TeacherStats
