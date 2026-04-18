from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime, date, time
from enum import Enum


# ========== Work Schedule Schemas ==========

class TeacherWorkScheduleCreate(BaseModel):
    """建立教師工作時段"""
    weekday: int = Field(..., ge=0, le=6, description="星期幾 (0=週一, 6=週日)")
    start_time: time = Field(..., description="開始時間")
    end_time: time = Field(..., description="結束時間")
    notes: Optional[str] = Field(None, description="備註")

    @model_validator(mode='after')
    def validate_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time 必須小於 end_time")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "weekday": 1,
                "start_time": "09:00:00",
                "end_time": "12:00:00",
                "notes": "週二上午時段",
            }]
        }
    }


class TeacherWorkScheduleBatchSet(BaseModel):
    """全量替換教師工作時段"""
    schedules: list[TeacherWorkScheduleCreate] = Field(..., description="工作時段列表")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "schedules": [
                    {"weekday": 1, "start_time": "09:00:00", "end_time": "12:00:00"},
                    {"weekday": 3, "start_time": "14:00:00", "end_time": "17:00:00"},
                    {"weekday": 5, "start_time": "09:00:00", "end_time": "12:00:00"},
                ],
            }]
        }
    }


class TeacherWorkScheduleResponse(BaseModel):
    """教師工作時段回應"""
    id: str
    teacher_contract_id: str
    weekday: int
    start_time: time
    end_time: time
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "teacher_contract_id": "660e8400-e29b-41d4-a716-446655440000",
                "weekday": 1,
                "start_time": "09:00:00",
                "end_time": "12:00:00",
                "notes": "週二上午時段",
                "created_at": "2026-03-01T10:00:00",
                "updated_at": "2026-03-01T10:00:00",
            }]
        }
    }


class ContractStatus(str, Enum):
    pending = "pending"
    active = "active"
    expired = "expired"
    terminated = "terminated"
    suspended = "suspended"


class EmploymentType(str, Enum):
    hourly = "hourly"
    full_time = "full_time"


class DetailType(str, Enum):
    course_rate = "course_rate"
    base_salary = "base_salary"
    allowance = "allowance"
    overtime_rate = "overtime_rate"


# ========== Contract Detail Schemas ==========

class TeacherContractDetailCreate(BaseModel):
    """建立教師合約明細"""
    detail_type: DetailType = Field(..., description="明細類型")
    course_id: Optional[str] = Field(None, description="課程 ID（僅 course_rate）")
    description: Optional[str] = Field(None, max_length=100, description="說明文字")
    amount: float = Field(..., ge=0, description="金額")
    notes: Optional[str] = Field(None, description="備註")

    @model_validator(mode='after')
    def validate_course_rate(self):
        if self.detail_type == DetailType.course_rate and not self.course_id:
            raise ValueError("course_rate 類型必須指定 course_id")
        if self.detail_type != DetailType.course_rate and self.course_id:
            raise ValueError("非 course_rate 類型不可指定 course_id")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "detail_type": "course_rate",
                "course_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "description": "英語會話課時薪",
                "amount": 800.0,
            }]
        }
    }


class TeacherContractDetailUpdate(BaseModel):
    """更新教師合約明細（不可改 detail_type 和 course_id）"""
    description: Optional[str] = Field(None, max_length=100, description="說明文字")
    amount: Optional[float] = Field(None, ge=0, description="金額")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "description": "英語會話課時薪（調整）",
                "amount": 850.0,
            }]
        }
    }


class TeacherContractDetailResponse(BaseModel):
    """教師合約明細回應"""
    id: str
    teacher_contract_id: str
    detail_type: DetailType
    course_id: Optional[str] = None
    course_name: Optional[str] = None
    description: Optional[str] = None
    amount: float
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "teacher_contract_id": "660e8400-e29b-41d4-a716-446655440000",
                "detail_type": "course_rate",
                "course_id": "770e8400-e29b-41d4-a716-446655440000",
                "course_name": "英語日常會話",
                "description": "英語會話課時薪",
                "amount": 800.0,
                "notes": None,
                "created_at": "2026-03-01T10:00:00",
                "updated_at": "2026-03-01T10:00:00",
            }]
        }
    }


# ========== Contract Schemas ==========

class TeacherContractBase(BaseModel):
    teacher_id: str = Field(..., description="教師 ID")
    contract_status: ContractStatus = Field(ContractStatus.pending, description="合約狀態")
    start_date: date = Field(..., description="合約開始日期")
    end_date: date = Field(..., description="合約結束日期")
    employment_type: EmploymentType = Field(EmploymentType.hourly, description="僱用類型")
    trial_completed_bonus: Optional[float] = Field(0, ge=0, description="試上完成獎金")
    trial_to_formal_bonus: Optional[float] = Field(0, ge=0, description="試上轉正獎金（轉正時補發差額）")
    work_start_time: Optional[time] = Field(None, description="正職上班開始時間")
    work_end_time: Optional[time] = Field(None, description="正職上班結束時間")
    notes: Optional[str] = Field(None, description="備註")


class TeacherContractCreate(TeacherContractBase):
    """建立教師合約的請求"""

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "teacher_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "contract_status": "active",
                "start_date": "2026-03-01",
                "end_date": "2026-08-31",
                "employment_type": "hourly",
                "trial_completed_bonus": 200.0,
                "trial_to_formal_bonus": 500.0,
            }]
        }
    }


class TeacherContractUpdate(BaseModel):
    """更新教師合約的請求"""
    teacher_id: Optional[str] = Field(None, description="教師 ID")
    contract_status: Optional[ContractStatus] = Field(None, description="合約狀態")
    start_date: Optional[date] = Field(None, description="合約開始日期")
    end_date: Optional[date] = Field(None, description="合約結束日期")
    employment_type: Optional[EmploymentType] = Field(None, description="僱用類型")
    trial_completed_bonus: Optional[float] = Field(None, ge=0, description="試上完成獎金")
    trial_to_formal_bonus: Optional[float] = Field(None, ge=0, description="試上轉正獎金（轉正時補發差額）")
    work_start_time: Optional[time] = Field(None, description="正職上班開始時間")
    work_end_time: Optional[time] = Field(None, description="正職上班結束時間")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "contract_status": "active",
                "employment_type": "full_time",
                "work_start_time": "09:00:00",
                "work_end_time": "18:00:00",
                "notes": "轉為正職教師",
            }]
        }
    }


class TeacherContractResponse(BaseModel):
    """教師合約回應"""
    id: str
    contract_no: str
    teacher_id: str
    contract_status: ContractStatus
    start_date: date
    end_date: date
    employment_type: EmploymentType = EmploymentType.hourly
    trial_completed_bonus: Optional[float] = 0
    trial_to_formal_bonus: Optional[float] = 0
    work_start_time: Optional[time] = None
    work_end_time: Optional[time] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 檔案相關
    contract_file_path: Optional[str] = None
    contract_file_name: Optional[str] = None
    contract_file_uploaded_at: Optional[datetime] = None
    # 關聯資料
    teacher_name: Optional[str] = None
    # 明細
    details: list[TeacherContractDetailResponse] = []
    total_amount: Optional[float] = None
    # 工作時段
    work_schedules: list[TeacherWorkScheduleResponse] = []
    # 附約
    addendums: list[dict] = []

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "contract_no": "TC-2026-001",
                "teacher_id": "660e8400-e29b-41d4-a716-446655440000",
                "contract_status": "active",
                "start_date": "2026-03-01",
                "end_date": "2026-08-31",
                "employment_type": "hourly",
                "trial_completed_bonus": 200.0,
                "trial_to_formal_bonus": 500.0,
                "work_start_time": None,
                "work_end_time": None,
                "notes": None,
                "created_at": "2026-03-01T10:00:00",
                "updated_at": "2026-03-01T10:00:00",
                "contract_file_path": None,
                "contract_file_name": None,
                "contract_file_uploaded_at": None,
                "teacher_name": "陳美玲",
                "details": [{
                    "id": "770e8400-e29b-41d4-a716-446655440000",
                    "teacher_contract_id": "550e8400-e29b-41d4-a716-446655440000",
                    "detail_type": "course_rate",
                    "course_id": "880e8400-e29b-41d4-a716-446655440000",
                    "course_name": "英語日常會話",
                    "description": "英語會話課時薪",
                    "amount": 800.0,
                    "notes": None,
                    "created_at": "2026-03-01T10:00:00",
                    "updated_at": "2026-03-01T10:00:00",
                }],
                "total_amount": 800.0,
                "work_schedules": [{
                    "id": "990e8400-e29b-41d4-a716-446655440000",
                    "teacher_contract_id": "550e8400-e29b-41d4-a716-446655440000",
                    "weekday": 1,
                    "start_time": "09:00:00",
                    "end_time": "12:00:00",
                    "notes": "週二上午時段",
                    "created_at": "2026-03-01T10:00:00",
                    "updated_at": "2026-03-01T10:00:00",
                }],
                "addendums": [],
            }]
        }
    }


class TeacherContractListResponse(BaseModel):
    """教師合約列表回應"""
    success: bool = True
    data: list[TeacherContractResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
