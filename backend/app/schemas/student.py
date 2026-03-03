from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


class StudentCreate(BaseModel):
    """建立學生"""
    student_no: str = Field(..., min_length=1, max_length=50, description="學生編號")
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    email: str = Field(..., max_length=255, description="Email")
    phone: Optional[str] = Field(None, max_length=20, description="電話")
    address: Optional[str] = Field(None, description="地址")
    birth_date: Optional[date] = Field(None, description="生日")
    student_type: str = Field("formal", description="學生類型 (formal/trial)")
    is_active: bool = Field(True, description="是否啟用")


class StudentUpdate(BaseModel):
    """更新學生"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    birth_date: Optional[date] = None
    student_type: Optional[str] = Field(None, description="學生類型 (formal/trial)")
    is_active: Optional[bool] = None


class StudentResponse(BaseModel):
    """學生回應"""
    id: str
    student_no: str
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None
    student_type: Optional[str] = "formal"
    is_active: bool = True
    email_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StudentListResponse(BaseModel):
    """學生列表回應"""
    success: bool = True
    data: list[StudentResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0


# ========== 試上轉正 ==========

class ConvertToFormalRequest(BaseModel):
    """試上轉正請求"""
    contract_no: str = Field(..., description="合約編號")
    total_lessons: int = Field(..., ge=1, description="總堂數")
    total_amount: float = Field(..., ge=0, description="合約總金額")
    start_date: date = Field(..., description="合約開始日期")
    end_date: date = Field(..., description="合約結束日期")
    teacher_id: Optional[str] = Field(None, description="指定教師 ID（計算轉正獎金）")
    booking_id: Optional[str] = Field(None, description="關聯的試上預約 ID")
    notes: Optional[str] = Field(None, description="備註")


class ConvertToFormalContractInfo(BaseModel):
    """轉正合約資訊"""
    id: str
    contract_no: str
    student_id: str
    contract_status: str
    start_date: date
    end_date: date
    total_lessons: int
    remaining_lessons: int
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConvertToFormalResponse(BaseModel):
    """試上轉正回應"""
    success: bool = True
    message: str = "轉正成功"
    student: StudentResponse
    contract: ConvertToFormalContractInfo
    bonus_recorded: bool = False
    bonus_amount: Optional[float] = None
