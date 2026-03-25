from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, time


# ============================================
# 子區塊 schemas
# ============================================

class StudentBasicInfo(BaseModel):
    id: str
    student_no: str
    name: str
    eng_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None
    student_type: Optional[str] = "formal"
    is_active: bool = True
    email_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class StudentAccountInfo(BaseModel):
    has_account: bool = False
    is_active: Optional[bool] = None
    role: Optional[str] = None


class StudentLineBinding(BaseModel):
    bound: bool = False
    line_display_name: Optional[str] = None
    line_picture_url: Optional[str] = None
    binding_status: Optional[str] = None


class StudentContractSummary(BaseModel):
    id: str
    contract_no: str
    contract_status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_lessons: int = 0
    remaining_lessons: int = 0
    total_amount: Optional[float] = None
    total_leave_allowed: int = 0
    used_leave_count: int = 0
    used_emergency_leave_count: int = 0
    is_recurring: bool = False
    # enriched
    teachers: list[str] = []
    addendum_count: int = 0


class StudentBookingSummary(BaseModel):
    id: str
    booking_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    booking_status: str = "pending"
    booking_type: Optional[str] = None
    teacher_name: Optional[str] = None
    course_name: Optional[str] = None


class StudentCourseSummary(BaseModel):
    id: str
    course_id: str
    course_name: Optional[str] = None
    course_code: Optional[str] = None
    enrolled_at: Optional[datetime] = None


class StudentPreferenceSummary(BaseModel):
    id: str
    course_name: Optional[str] = None
    min_teacher_level: Optional[int] = None
    primary_teacher_name: Optional[str] = None


class StudentLeaveSummary(BaseModel):
    id: str
    leave_date: Optional[date] = None
    leave_status: str = "pending"
    leave_type: Optional[str] = None
    reason: Optional[str] = None
    booking_date: Optional[date] = None


class StudentStats(BaseModel):
    total_bookings: int = 0
    completed_bookings: int = 0
    cancelled_bookings: int = 0
    pending_bookings: int = 0
    upcoming_bookings: int = 0
    total_contracts: int = 0
    active_contracts: int = 0
    total_remaining_lessons: int = 0
    total_leaves_used: int = 0
    total_courses_enrolled: int = 0


# ============================================
# 主回應
# ============================================

class StudentViewResponse(BaseModel):
    student: StudentBasicInfo
    account: StudentAccountInfo
    line_binding: StudentLineBinding
    contracts: list[StudentContractSummary] = []
    bookings_recent: list[StudentBookingSummary] = []
    courses: list[StudentCourseSummary] = []
    teacher_preferences: list[StudentPreferenceSummary] = []
    leave_records_recent: list[StudentLeaveSummary] = []
    stats: StudentStats
