from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date


class EmployeeCreate(BaseModel):
    """建立員工"""
    employee_no: str = Field(..., min_length=1, max_length=50, description="員工編號")
    employee_type: str = Field(..., description="員工類型 (admin/full_time/part_time/intern)")
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    email: str = Field(..., max_length=255, description="Email")
    phone: Optional[str] = Field(None, max_length=20, description="電話")
    address: Optional[str] = Field(None, description="地址")
    hire_date: date = Field(..., description="到職日")
    termination_date: Optional[date] = Field(None, description="離職日")
    is_active: bool = Field(True, description="是否啟用")


class EmployeeUpdate(BaseModel):
    """更新員工"""
    employee_type: Optional[str] = Field(None, description="員工類型 (admin/full_time/part_time/intern)")
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    is_active: Optional[bool] = None


class EmployeeResponse(BaseModel):
    """員工回應"""
    id: str
    employee_no: str
    employee_type: str
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmployeeListResponse(BaseModel):
    """員工列表回應"""
    success: bool = True
    data: list[EmployeeResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
