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

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "teacher_no": "T001",
                "name": "陳老師",
                "email": "teacher@eop-education.com",
                "phone": "0923456789",
                "address": "台北市信義區松仁路50號",
                "bio": "10年英語教學經驗，專攻兒童英語與會話訓練",
                "avatar_url": "https://s3.amazonaws.com/eop/avatars/teacher001.jpg",
                "teacher_level": 3,
                "is_active": True,
                "email_verified_at": "2026-01-10T10:00:00",
                "created_at": "2026-01-05T09:00:00",
            }]
        }
    }


class TeacherAccountInfo(BaseModel):
    has_account: bool = False
    is_active: Optional[bool] = None
    role: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "has_account": True,
                "is_active": True,
                "role": "teacher",
            }]
        }
    }


class TeacherLineBinding(BaseModel):
    bound: bool = False
    line_display_name: Optional[str] = None
    line_picture_url: Optional[str] = None
    binding_status: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "bound": True,
                "line_display_name": "陳老師",
                "line_picture_url": "https://profile.line-scdn.net/def456",
                "binding_status": "active",
            }]
        }
    }


class TeacherContractSummary(BaseModel):
    id: str
    contract_no: str
    contract_status: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    employment_type: Optional[str] = None
    notes: Optional[str] = None
    addendum_count: int = 0

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "contract_no": "TC20260101001",
                "contract_status": "active",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "employment_type": "part_time",
                "notes": "每週固定排課 12 小時",
                "addendum_count": 0,
            }]
        }
    }


class TeacherBookingSummary(BaseModel):
    id: str
    booking_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    booking_status: str = "pending"
    booking_type: Optional[str] = None
    student_name: Optional[str] = None
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
                "student_name": "王小明",
                "course_name": "英語初級會話",
            }]
        }
    }


class TeacherBonusSummary(BaseModel):
    id: str
    bonus_type: Optional[str] = None
    amount: Optional[float] = None
    bonus_date: Optional[date] = None
    description: Optional[str] = None
    student_name: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "bonus_type": "trial_to_formal",
                "amount": 500.0,
                "bonus_date": "2026-04-10",
                "description": "學生王小明試上轉正獎金",
                "student_name": "王小明",
            }]
        }
    }


class TeacherWorkScheduleSummary(BaseModel):
    id: str
    weekday: int
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    notes: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "weekday": 1,
                "start_time": "09:00",
                "end_time": "12:00",
                "notes": "週一上午固定時段",
            }]
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "total_bookings": 120,
                "completed_bookings": 95,
                "cancelled_bookings": 5,
                "pending_bookings": 3,
                "upcoming_bookings": 17,
                "total_contracts": 2,
                "active_contracts": 1,
                "total_bonus_amount": 15000.0,
                "total_bonus_count": 12,
                "total_students_taught": 25,
            }]
        }
    }


class TeacherViewResponse(BaseModel):
    teacher: TeacherBasicInfo
    account: TeacherAccountInfo
    line_binding: TeacherLineBinding
    contracts: list[TeacherContractSummary] = []
    bookings_recent: list[TeacherBookingSummary] = []
    bonus_records_recent: list[TeacherBonusSummary] = []
    work_schedules: list[TeacherWorkScheduleSummary] = []
    stats: TeacherStats

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "teacher": {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "teacher_no": "T001",
                    "name": "陳老師",
                    "email": "teacher@eop-education.com",
                    "phone": "0923456789",
                    "address": "台北市信義區松仁路50號",
                    "bio": "10年英語教學經驗，專攻兒童英語與會話訓練",
                    "avatar_url": "https://s3.amazonaws.com/eop/avatars/teacher001.jpg",
                    "teacher_level": 3,
                    "is_active": True,
                    "email_verified_at": "2026-01-10T10:00:00",
                    "created_at": "2026-01-05T09:00:00",
                },
                "account": {
                    "has_account": True,
                    "is_active": True,
                    "role": "teacher",
                },
                "line_binding": {
                    "bound": True,
                    "line_display_name": "陳老師",
                    "line_picture_url": "https://profile.line-scdn.net/def456",
                    "binding_status": "active",
                },
                "contracts": [{
                    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "contract_no": "TC20260101001",
                    "contract_status": "active",
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
                    "employment_type": "part_time",
                    "notes": "每週固定排課 12 小時",
                    "addendum_count": 0,
                }],
                "bookings_recent": [{
                    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                    "booking_date": "2026-04-15",
                    "start_time": "14:00",
                    "end_time": "15:00",
                    "booking_status": "confirmed",
                    "booking_type": "regular",
                    "student_name": "王小明",
                    "course_name": "英語初級會話",
                }],
                "bonus_records_recent": [{
                    "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
                    "bonus_type": "trial_to_formal",
                    "amount": 500.0,
                    "bonus_date": "2026-04-10",
                    "description": "學生王小明試上轉正獎金",
                    "student_name": "王小明",
                }],
                "work_schedules": [{
                    "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
                    "weekday": 1,
                    "start_time": "09:00",
                    "end_time": "12:00",
                    "notes": "週一上午固定時段",
                }],
                "stats": {
                    "total_bookings": 120,
                    "completed_bookings": 95,
                    "cancelled_bookings": 5,
                    "pending_bookings": 3,
                    "upcoming_bookings": 17,
                    "total_contracts": 2,
                    "active_contracts": 1,
                    "total_bonus_amount": 15000.0,
                    "total_bonus_count": 12,
                    "total_students_taught": 25,
                },
            }]
        }
    }
