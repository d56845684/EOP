from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TeacherCreate(BaseModel):
    """建立教師"""
    teacher_no: str = Field(..., min_length=1, max_length=50, description="教師編號")
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    email: str = Field(..., max_length=255, description="Email")
    phone: Optional[str] = Field(None, max_length=20, description="電話")
    address: Optional[str] = Field(None, description="地址")
    bio: Optional[str] = Field(None, description="簡介")
    teacher_level: int = Field(1, ge=1, description="教師等級")
    is_active: bool = Field(True, description="是否啟用")


class TeacherUpdate(BaseModel):
    """更新教師"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    bio: Optional[str] = None
    teacher_level: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class TeacherResponse(BaseModel):
    """教師回應"""
    id: str
    teacher_no: str
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None
    teacher_level: int = 1
    is_active: bool = True
    email_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeacherListResponse(BaseModel):
    """教師列表回應"""
    success: bool = True
    data: list[TeacherResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
