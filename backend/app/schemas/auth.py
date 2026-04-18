from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional, Literal
from datetime import date

# 員工類型定義
EmployeeType = Literal["admin", "full_time", "part_time", "intern"]
RoleType = Literal["student", "teacher", "employee"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# 公開註冊允許的角色（employee 只能透過 invite 流程建立）
PublicRoleType = Literal["student", "teacher"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: PublicRoleType = "student"

    # 共用欄位
    phone: Optional[str] = Field(None, description="聯絡電話")
    address: Optional[str] = Field(None, description="地址")

    # 學生專用欄位
    birth_date: Optional[date] = Field(None, description="生日（僅學生）")
    emergency_contact_name: Optional[str] = Field(None, description="緊急聯絡人姓名（僅學生）")
    emergency_contact_phone: Optional[str] = Field(None, description="緊急聯絡人電話（僅學生）")

    # 教師專用欄位
    bio: Optional[str] = Field(None, description="教師簡介（僅教師）")

    @model_validator(mode="after")
    def validate_role_fields(self):
        # 清除不屬於該角色的欄位
        if self.role != "student":
            self.birth_date = None
            self.emergency_contact_name = None
            self.emergency_contact_phone = None
        if self.role != "teacher":
            self.bio = None

        return self


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    id: str
    email: str
    role: str
    role_id: Optional[str] = Field(None, description="角色 UUID")
    email_confirmed: bool = False
    created_at: Optional[str] = None
    employee_type: Optional[str] = Field(
        None,
        description="員工類型（若為員工身份）"
    )
    permission_level: int = Field(
        0,
        description="權限等級"
    )
    must_change_password: bool = Field(
        False,
        description="是否需要強制變更密碼"
    )
    teacher_id: Optional[str] = Field(None, description="教師 ID")
    student_id: Optional[str] = Field(None, description="學生 ID")
    employee_id: Optional[str] = Field(None, description="員工 ID")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "email": "employee@eop-education.com",
                "role": "employee",
                "role_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "email_confirmed": True,
                "created_at": "2026-01-10T08:00:00",
                "employee_type": "full_time",
                "permission_level": 5,
                "must_change_password": False,
                "teacher_id": None,
                "student_id": None,
                "employee_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
            }]
        }
    }

class LoginResponse(BaseModel):
    success: bool = True
    message: str = "登入成功"
    user: UserInfo
    tokens: TokenPair

class LogoutRequest(BaseModel):
    logout_all_devices: bool = False

class RefreshResponse(BaseModel):
    success: bool = True
    tokens: TokenPair

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordUpdateRequest(BaseModel):
    current_password: str
    new_password: str

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "current_password": "OldPassword123!",
                "new_password": "NewPassword456!",
            }]
        }
    }