from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime, date
from enum import Enum


class ContractStatus(str, Enum):
    pending = "pending"
    active = "active"
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


class StudentContractDetailUpdate(BaseModel):
    """更新學生合約明細（不可改 detail_type 和 course_id）"""
    description: Optional[str] = Field(None, max_length=100, description="說明文字")
    amount: Optional[float] = Field(None, description="金額")
    notes: Optional[str] = Field(None, description="備註")


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

    class Config:
        from_attributes = True


# ========== Leave Record Schemas ==========

class StudentContractLeaveRecordCreate(BaseModel):
    """建立請假紀錄"""
    leave_date: date = Field(..., description="請假日期")
    reason: Optional[str] = Field(None, description="請假原因")


class StudentContractLeaveRecordResponse(BaseModel):
    """請假紀錄回應"""
    id: str
    student_contract_id: str
    leave_date: date
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== Contract Schemas ==========

class StudentContractBase(BaseModel):
    student_id: str = Field(..., description="學生 ID")
    contract_status: ContractStatus = Field(ContractStatus.pending, description="合約狀態")
    start_date: date = Field(..., description="合約開始日期")
    end_date: date = Field(..., description="合約結束日期")
    total_lessons: int = Field(..., ge=1, description="總堂數")
    remaining_lessons: int = Field(..., ge=0, description="剩餘堂數")
    total_amount: float = Field(..., ge=0, description="合約總金額")
    total_leave_allowed: Optional[int] = Field(None, ge=0, description="可請假次數（預設 = total_lessons * 2）")
    is_recurring: bool = Field(False, description="是否為帶狀學生（固定時間/課程/老師）")
    notes: Optional[str] = Field(None, description="備註")


class StudentContractCreate(StudentContractBase):
    """建立學生合約的請求"""
    pass


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
    # 明細 + 請假
    details: list[StudentContractDetailResponse] = []
    leave_records: list[StudentContractLeaveRecordResponse] = []

    class Config:
        from_attributes = True


class StudentContractListResponse(BaseModel):
    """學生合約列表回應"""
    success: bool = True
    data: list[StudentContractResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
