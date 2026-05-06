from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime, date
from enum import Enum


class ContractStatus(str, Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"
    expired = "expired"
    terminated = "terminated"


class DetailType(str, Enum):
    lesson_price = "lesson_price"
    discount = "discount"
    compensation = "compensation"


# ========== Contract Detail Schemas ==========

class StudentContractDetailCreate(BaseModel):
    """建立學生合約明細"""
    detail_type: DetailType = Field(..., description="明細類型")
    course_id: Optional[str] = Field(None, description="課程 ID（僅 lesson_price）")
    description: Optional[str] = Field(None, max_length=100, description="說明文字")
    amount: float = Field(..., description="金額")
    notes: Optional[str] = Field(None, description="備註")

    @model_validator(mode='after')
    def validate_lesson_price(self):
        if self.detail_type == DetailType.lesson_price and not self.course_id:
            raise ValueError("lesson_price 類型必須指定 course_id")
        if self.detail_type != DetailType.lesson_price and self.course_id:
            raise ValueError("非 lesson_price 類型不可指定 course_id")
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "detail_type": "lesson_price",
                "course_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "description": "英語會話課程單價",
                "amount": 1500.0,
            }]
        }
    }


class StudentContractDetailUpdate(BaseModel):
    """更新學生合約明細（不可改 detail_type 和 course_id）"""
    description: Optional[str] = Field(None, max_length=100, description="說明文字")
    amount: Optional[float] = Field(None, description="金額")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "description": "英語會話課程單價（調整）",
                "amount": 1600.0,
            }]
        }
    }


class StudentContractDetailResponse(BaseModel):
    """學生合約明細回應"""
    id: str
    student_contract_id: str
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
                "student_contract_id": "660e8400-e29b-41d4-a716-446655440000",
                "detail_type": "lesson_price",
                "course_id": "770e8400-e29b-41d4-a716-446655440000",
                "course_name": "英語日常會話",
                "description": "英語會話課程單價",
                "amount": 1500.0,
                "notes": None,
                "created_at": "2026-03-01T10:00:00",
                "updated_at": "2026-03-01T10:00:00",
            }]
        }
    }


# ========== Leave Record Schemas ==========

class StudentContractLeaveRecordCreate(BaseModel):
    """建立請假紀錄"""
    leave_date: date = Field(..., description="請假日期")
    reason: Optional[str] = Field(None, description="請假原因")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "leave_date": "2026-04-20",
                "reason": "家庭旅遊",
            }]
        }
    }


class StudentContractLeaveRecordResponse(BaseModel):
    """請假紀錄回應"""
    id: str
    student_contract_id: str
    leave_date: date
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "student_contract_id": "660e8400-e29b-41d4-a716-446655440000",
                "leave_date": "2026-04-20",
                "reason": "家庭旅遊",
                "created_at": "2026-04-15T14:00:00",
            }]
        }
    }


# ========== Contract Schemas ==========

class StudentContractBase(BaseModel):
    student_id: str = Field(..., description="學生 ID")
    contract_status: ContractStatus = Field(ContractStatus.pending, description="合約狀態")
    start_date: date = Field(..., description="合約開始日期")
    end_date: date = Field(..., description="合約結束日期")
    total_lessons: int = Field(..., ge=1, description="總堂數")
    remaining_lessons: int = Field(..., ge=0, description="剩餘堂數")
    total_amount: float = Field(..., ge=0, description="合約總金額")
    total_leave_allowed: Optional[int] = Field(None, ge=0, description="可請假次數（預設 = ceil(total_lessons * 0.2)）")
    is_recurring: bool = Field(False, description="是否為帶狀學生（固定時間/課程/老師）")
    notes: Optional[str] = Field(None, description="備註")


class StudentContractCreate(StudentContractBase):
    """建立學生合約的請求"""

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "student_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "contract_status": "active",
                "start_date": "2026-03-01",
                "end_date": "2026-08-31",
                "total_lessons": 48,
                "remaining_lessons": 48,
                "total_amount": 72000.0,
                "is_recurring": True,
            }]
        }
    }


class StudentContractUpdate(BaseModel):
    """更新學生合約的請求"""
    student_id: Optional[str] = Field(None, description="學生 ID")
    contract_status: Optional[ContractStatus] = Field(None, description="合約狀態")
    start_date: Optional[date] = Field(None, description="合約開始日期")
    end_date: Optional[date] = Field(None, description="合約結束日期")
    total_lessons: Optional[int] = Field(None, ge=1, description="總堂數")
    remaining_lessons: Optional[int] = Field(None, ge=0, description="剩餘堂數")
    total_amount: Optional[float] = Field(None, ge=0, description="合約總金額")
    total_leave_allowed: Optional[int] = Field(None, ge=0, description="可請假次數")
    is_recurring: Optional[bool] = Field(None, description="是否為帶狀學生")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "contract_status": "active",
                "remaining_lessons": 40,
                "notes": "已完成八堂課",
            }]
        }
    }


class StudentContractResponse(BaseModel):
    """學生合約回應"""
    id: str
    contract_no: str
    student_id: str
    contract_status: ContractStatus
    start_date: date
    end_date: date
    total_lessons: int
    remaining_lessons: int
    total_amount: Optional[float] = None
    total_leave_allowed: int = 0
    used_leave_count: int = 0
    used_emergency_leave_count: int = 0
    emergency_leave_quota: Optional[int] = None  # enrich 計算: ceil(total_lessons * 0.2)
    remaining_emergency_leave_count: Optional[int] = None  # enrich 計算: max(0, quota - used)
    is_recurring: bool = False
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 檔案相關
    contract_file_path: Optional[str] = None
    contract_file_name: Optional[str] = None
    contract_file_uploaded_at: Optional[datetime] = None
    # 關聯資料
    student_name: Optional[str] = None
    student_phone: Optional[str] = None
    student_id_number: Optional[str] = None
    # 明細 + 請假
    details: list[StudentContractDetailResponse] = []
    leave_records: list[StudentContractLeaveRecordResponse] = []
    # 附約
    addendums: list[dict] = []

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "contract_no": "SC-2026-001",
                "student_id": "660e8400-e29b-41d4-a716-446655440000",
                "contract_status": "active",
                "start_date": "2026-03-01",
                "end_date": "2026-08-31",
                "total_lessons": 48,
                "remaining_lessons": 40,
                "total_amount": 72000.0,
                "total_leave_allowed": 10,
                "used_leave_count": 1,
                "used_emergency_leave_count": 0,
                "emergency_leave_quota": 10,
                "is_recurring": True,
                "notes": None,
                "created_at": "2026-03-01T10:00:00",
                "updated_at": "2026-03-15T14:00:00",
                "contract_file_path": None,
                "contract_file_name": None,
                "contract_file_uploaded_at": None,
                "student_name": "王小明",
                "student_phone": "0912345678",
                "student_id_number": None,
                "details": [{
                    "id": "770e8400-e29b-41d4-a716-446655440000",
                    "student_contract_id": "550e8400-e29b-41d4-a716-446655440000",
                    "detail_type": "lesson_price",
                    "course_id": "880e8400-e29b-41d4-a716-446655440000",
                    "course_name": "英語日常會話",
                    "description": "英語會話課程單價",
                    "amount": 1500.0,
                    "notes": None,
                    "created_at": "2026-03-01T10:00:00",
                    "updated_at": "2026-03-01T10:00:00",
                }],
                "leave_records": [{
                    "id": "990e8400-e29b-41d4-a716-446655440000",
                    "student_contract_id": "550e8400-e29b-41d4-a716-446655440000",
                    "leave_date": "2026-04-20",
                    "reason": "家庭旅遊",
                    "created_at": "2026-04-15T14:00:00",
                }],
                "addendums": [],
            }]
        }
    }


class StudentContractListResponse(BaseModel):
    """學生合約列表回應"""
    success: bool = True
    data: list[StudentContractResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
