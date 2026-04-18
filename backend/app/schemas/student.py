from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, date


class StudentCreate(BaseModel):
    """建立學生"""
    student_no: Optional[str] = Field(None, max_length=50, description="學生編號（留空自動產生 EOPS 格式）")
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    eng_name: Optional[str] = Field(None, max_length=100, description="英文名")
    email: EmailStr = Field(..., description="Email")
    phone: Optional[str] = Field(None, max_length=20, description="電話")
    address: Optional[str] = Field(None, description="地址")
    birth_date: Optional[date] = Field(None, description="生日")
    id_number: Optional[str] = Field(None, max_length=20, description="身分證字號")
    student_type: str = Field("formal", description="學生類型 (formal/trial)")
    is_active: bool = Field(True, description="是否啟用")
    google_drive_folder_id: Optional[str] = Field(None, description="Google Drive 資料夾 ID")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name": "王小明",
                "email": "xiaoming.wang@example.com",
                "eng_name": "Ming",
                "phone": "0912345678",
                "birth_date": "2015-03-15",
                "student_type": "formal",
            }]
        }
    }


class StudentUpdate(BaseModel):
    """更新學生"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    eng_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    birth_date: Optional[date] = None
    id_number: Optional[str] = Field(None, max_length=20)
    student_type: Optional[str] = Field(None, description="學生類型 (formal/trial)")
    is_active: Optional[bool] = None
    google_drive_folder_id: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "name": "王小明",
                "phone": "0922333444",
                "student_type": "formal",
            }]
        }
    }


class StudentResponse(BaseModel):
    """學生回應"""
    id: str
    student_no: str
    name: str
    eng_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None
    id_number: Optional[str] = None
    student_type: Optional[str] = "formal"
    student_status: Optional[str] = "trial"
    is_active: bool = True
    google_drive_folder_id: Optional[str] = None
    email_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "student_no": "EOPS001",
                "name": "王小明",
                "eng_name": "Ming",
                "email": "xiaoming.wang@example.com",
                "phone": "0912345678",
                "address": "台北市大安區忠孝東路100號",
                "birth_date": "2015-03-15",
                "id_number": None,
                "student_type": "formal",
                "student_status": "formal",
                "is_active": True,
                "google_drive_folder_id": None,
                "email_verified_at": "2026-03-01T09:00:00",
                "created_at": "2026-03-01T09:00:00",
                "updated_at": "2026-03-01T09:00:00",
            }]
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "contract_no": "SC-2026-001",
                "total_lessons": 24,
                "total_amount": 36000.0,
                "start_date": "2026-02-01",
                "end_date": "2026-07-31",
            }]
        }
    }


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

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "660e8400-e29b-41d4-a716-446655440000",
                "contract_no": "SC-2026-001",
                "student_id": "550e8400-e29b-41d4-a716-446655440000",
                "contract_status": "active",
                "start_date": "2026-02-01",
                "end_date": "2026-07-31",
                "total_lessons": 24,
                "remaining_lessons": 24,
                "notes": None,
                "created_at": "2026-02-01T10:00:00",
            }]
        }
    }


class ConvertToFormalResponse(BaseModel):
    """試上轉正回應"""
    success: bool = True
    message: str = "轉正成功"
    student: StudentResponse
    contract: ConvertToFormalContractInfo
    bonus_recorded: bool = False
    bonus_amount: Optional[float] = None

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "success": True,
                "message": "轉正成功",
                "student": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "student_no": "EOPS001",
                    "name": "王小明",
                    "eng_name": "Ming",
                    "email": "xiaoming.wang@example.com",
                    "phone": "0912345678",
                    "student_type": "formal",
                    "student_status": "formal",
                    "is_active": True,
                    "created_at": "2026-03-01T09:00:00",
                    "updated_at": "2026-03-01T09:00:00",
                },
                "contract": {
                    "id": "660e8400-e29b-41d4-a716-446655440000",
                    "contract_no": "SC-2026-001",
                    "student_id": "550e8400-e29b-41d4-a716-446655440000",
                    "contract_status": "active",
                    "start_date": "2026-02-01",
                    "end_date": "2026-07-31",
                    "total_lessons": 24,
                    "remaining_lessons": 24,
                    "created_at": "2026-02-01T10:00:00",
                },
                "bonus_recorded": True,
                "bonus_amount": 500.0,
            }]
        }
    }
