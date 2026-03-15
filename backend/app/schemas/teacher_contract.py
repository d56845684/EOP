from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime, date, time
from enum import Enum


class ContractStatus(str, Enum):
    pending = "pending"
    active = "active"
    expired = "expired"
    terminated = "terminated"


class EmploymentType(str, Enum):
    hourly = "hourly"
    full_time = "full_time"


class DetailType(str, Enum):
    course_rate = "course_rate"
    base_salary = "base_salary"
    allowance = "allowance"


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


class TeacherContractDetailUpdate(BaseModel):
    """更新教師合約明細（不可改 detail_type 和 course_id）"""
    description: Optional[str] = Field(None, max_length=100, description="說明文字")
    amount: Optional[float] = Field(None, ge=0, description="金額")
    notes: Optional[str] = Field(None, description="備註")


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

    class Config:
        from_attributes = True


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
    pass


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

    class Config:
        from_attributes = True


class TeacherContractListResponse(BaseModel):
    """教師合約列表回應"""
    success: bool = True
    data: list[TeacherContractResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
