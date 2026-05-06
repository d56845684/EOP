from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, date

from app.schemas._validators import OptionalDate


class StudentCreate(BaseModel):
    """建立學生"""
    student_no: Optional[str] = Field(None, max_length=50, description="學生編號（留空自動產生 EOPS 格式）")
    name: str = Field(..., min_length=1, max_length=100, description="姓名")
    eng_name: str = Field(..., min_length=1, max_length=100, description="英文名（必填）")
    email: EmailStr = Field(..., description="Email")
    phone: str = Field(..., min_length=1, max_length=20, description="電話（必填）")
    address: Optional[str] = Field(None, description="地址")
    birth_date: OptionalDate = Field(None, description="生日（空字串自動轉 None）")
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
    birth_date: OptionalDate = None
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
    """試上轉正請求

    新流程：必須先建立 pending 合約並上傳 PDF，轉正只負責 activate。
    """
    student_contract_id: str = Field(..., description="待確認合約 ID（contract_status=pending 且已上傳 PDF）")
    teacher_id: Optional[str] = Field(None, description="指定教師 ID（計算轉正獎金）")
    booking_id: Optional[str] = Field(None, description="關聯的試上預約 ID")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "student_contract_id": "660e8400-e29b-41d4-a716-446655440000",
                "teacher_id": "770e8400-e29b-41d4-a716-446655440000",
                "booking_id": "880e8400-e29b-41d4-a716-446655440000",
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
    bonus_error: Optional[str] = None  # 獎金處理失敗訊息（已記到 system_alerts）

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
