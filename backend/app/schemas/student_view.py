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

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "student_no": "S001",
                "name": "王小明",
                "eng_name": "Ming Wang",
                "email": "student@eop-education.com",
                "phone": "0912345678",
                "address": "台北市大安區忠孝東路100號",
                "birth_date": "2010-05-15",
                "student_type": "formal",
                "is_active": True,
                "email_verified_at": "2026-01-20T10:00:00",
                "created_at": "2026-01-15T09:00:00",
            }]
        }
    }


class StudentAccountInfo(BaseModel):
    has_account: bool = False
    is_active: Optional[bool] = None
    role: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "has_account": True,
                "is_active": True,
                "role": "student",
            }]
        }
    }


class StudentLineBinding(BaseModel):
    bound: bool = False
    line_display_name: Optional[str] = None
    line_picture_url: Optional[str] = None
    binding_status: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "bound": True,
                "line_display_name": "小明",
                "line_picture_url": "https://profile.line-scdn.net/abc123",
                "binding_status": "active",
            }]
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "contract_no": "SC20260101001",
                "contract_status": "active",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "total_lessons": 48,
                "remaining_lessons": 30,
                "total_amount": 96000.0,
                "total_leave_allowed": 4,
                "used_leave_count": 1,
                "used_emergency_leave_count": 0,
                "is_recurring": False,
                "teachers": ["陳老師", "李老師"],
                "addendum_count": 0,
            }]
        }
    }


class StudentBookingSummary(BaseModel):
    id: str
    booking_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    booking_status: str = "pending"
    booking_type: Optional[str] = None
    teacher_name: Optional[str] = None
    course_name: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "booking_date": "2026-04-15",
                "start_time": "14:00",
                "end_time": "15:00",
                "booking_status": "confirmed",
                "booking_type": "regular",
                "teacher_name": "陳老師",
                "course_name": "英語初級會話",
            }]
        }
    }


class StudentCourseSummary(BaseModel):
    id: str
    course_id: str
    course_name: Optional[str] = None
    course_code: Optional[str] = None
    enrolled_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "course_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "course_name": "英語初級會話",
                "course_code": "ENG-A1",
                "enrolled_at": "2026-03-01T10:00:00",
            }]
        }
    }


class StudentPreferenceSummary(BaseModel):
    id: str
    course_name: Optional[str] = None
    min_teacher_level: Optional[int] = None
    primary_teacher_name: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "course_name": "英語初級會話",
                "min_teacher_level": 3,
                "primary_teacher_name": "陳老師",
            }]
        }
    }


class StudentLeaveSummary(BaseModel):
    id: str
    leave_date: Optional[date] = None
    leave_status: str = "pending"
    leave_type: Optional[str] = None
    reason: Optional[str] = None
    booking_date: Optional[date] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "leave_date": "2026-04-15",
                "leave_status": "approved",
                "leave_type": "normal",
                "reason": "身體不適",
                "booking_date": "2026-04-15",
            }]
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "total_bookings": 25,
                "completed_bookings": 18,
                "cancelled_bookings": 2,
                "pending_bookings": 1,
                "upcoming_bookings": 4,
                "total_contracts": 2,
                "active_contracts": 1,
                "total_remaining_lessons": 30,
                "total_leaves_used": 1,
                "total_courses_enrolled": 2,
            }]
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "student": {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "student_no": "S001",
                    "name": "王小明",
                    "eng_name": "Ming Wang",
                    "email": "student@eop-education.com",
                    "phone": "0912345678",
                    "address": "台北市大安區忠孝東路100號",
                    "birth_date": "2010-05-15",
                    "student_type": "formal",
                    "is_active": True,
                    "email_verified_at": "2026-01-20T10:00:00",
                    "created_at": "2026-01-15T09:00:00",
                },
                "account": {
                    "has_account": True,
                    "is_active": True,
                    "role": "student",
                },
                "line_binding": {
                    "bound": True,
                    "line_display_name": "小明",
                    "line_picture_url": "https://profile.line-scdn.net/abc123",
                    "binding_status": "active",
                },
                "contracts": [{
                    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "contract_no": "SC20260101001",
                    "contract_status": "active",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "total_lessons": 48,
                    "remaining_lessons": 30,
                    "total_amount": 96000.0,
                    "total_leave_allowed": 4,
                    "used_leave_count": 1,
                    "used_emergency_leave_count": 0,
                    "is_recurring": False,
                    "teachers": ["陳老師"],
                    "addendum_count": 0,
                }],
                "bookings_recent": [{
                    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    "booking_date": "2026-04-15",
                    "start_time": "14:00",
                    "end_time": "15:00",
                    "booking_status": "confirmed",
                    "booking_type": "regular",
                    "teacher_name": "陳老師",
                    "course_name": "英語初級會話",
                }],
                "courses": [{
                    "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
                    "course_id": "e5f6a7b8-c9d0-1234-efab-345678901234",
                    "course_name": "英語初級會話",
                    "course_code": "ENG-A1",
                    "enrolled_at": "2026-03-01T10:00:00",
                }],
                "teacher_preferences": [{
                    "id": "f6a7b8c9-d0e1-2345-fabc-456789012345",
                    "course_name": "英語初級會話",
                    "min_teacher_level": 3,
                    "primary_teacher_name": "陳老師",
                }],
                "leave_records_recent": [{
                    "id": "a7b8c9d0-e1f2-3456-abcd-567890123456",
                    "leave_date": "2026-04-10",
                    "leave_status": "approved",
                    "leave_type": "normal",
                    "reason": "身體不適",
                    "booking_date": "2026-04-10",
                }],
                "stats": {
                    "total_bookings": 25,
                    "completed_bookings": 18,
                    "cancelled_bookings": 2,
                    "pending_bookings": 1,
                    "upcoming_bookings": 4,
                    "total_contracts": 2,
                    "active_contracts": 1,
                    "total_remaining_lessons": 30,
                    "total_leaves_used": 1,
                    "total_courses_enrolled": 2,
                },
            }]
        }
    }
