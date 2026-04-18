from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class TeacherCreate(BaseModel):
    """建立教師"""
    teacher_no: Optional[str] = Field(None, max_length=50, description="教師編號（留空自動產生 EOPT 格式）")
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    email: EmailStr = Field(..., description="Email")
    phone: Optional[str] = Field(None, max_length=20, description="電話")
    address: Optional[str] = Field(None, description="地址")
    bio: Optional[str] = Field(None, description="簡介")
    teacher_level: int = Field(1, ge=1, description="教師等級")
    is_active: bool = Field(True, description="是否啟用")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name": "陳美玲",
                "email": "meiling.chen@example.com",
                "phone": "0933456789",
                "bio": "英語教學經驗十年，擅長兒童美語與會話教學",
                "teacher_level": 2,
            }]
        }
    }


class TeacherUpdate(BaseModel):
    """更新教師"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    bio: Optional[str] = None
    teacher_level: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name": "陳美玲",
                "phone": "0933456789",
                "teacher_level": 3,
            }]
        }
    }


class TeacherSelfUpdate(BaseModel):
    """教師自行更新的欄位"""
    bio: Optional[str] = Field(None, description="簡介")
    phone: Optional[str] = Field(None, max_length=20, description="電話")
    address: Optional[str] = Field(None, description="地址")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "bio": "10 年英語教學經驗，專長兒童美語",
                "phone": "0912345678",
                "address": "台北市大安區",
            }]
        }
    }


class TeacherResponse(BaseModel):
    """教師回應"""
    id: str
    teacher_no: str
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    teacher_level: int = 1
    is_active: bool = True
    email_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "teacher_no": "EOPT001",
                "name": "陳美玲",
                "email": "meiling.chen@example.com",
                "phone": "0933456789",
                "address": "台北市信義區松仁路50號",
                "bio": "英語教學經驗十年，擅長兒童美語與會話教學",
                "avatar_url": None,
                "teacher_level": 2,
                "is_active": True,
                "email_verified_at": "2026-02-15T08:30:00",
                "created_at": "2026-02-15T08:30:00",
                "updated_at": "2026-02-15T08:30:00",
            }]
        }
    }


class TeacherListResponse(BaseModel):
    """教師列表回應"""
    success: bool = True
    data: list[TeacherResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
