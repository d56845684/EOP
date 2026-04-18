from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum


class ContractType(str, Enum):
    student = "student"
    teacher = "teacher"


class AddendumStatus(str, Enum):
    pending = "pending"
    active = "active"
    expired = "expired"
    terminated = "terminated"


class ContractAddendumCreate(BaseModel):
    """建立附約（parent_contract_id 和 contract_type 從 URL 路徑取得）"""
    new_end_date: date = Field(..., description="展延後結束日期")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "new_end_date": "2027-03-31",
                "notes": "合約展延至下學期結束",
            }]
        }
    }


class ContractAddendumUpdate(BaseModel):
    """更新附約"""
    new_end_date: Optional[date] = Field(None, description="展延後結束日期")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "new_end_date": "2027-06-30",
                "notes": "調整展延結束日期至暑假",
            }]
        }
    }


class ContractAddendumResponse(BaseModel):
    """附約回應"""
    id: str
    addendum_no: str
    contract_type: ContractType
    parent_contract_id: str
    original_end_date: date
    new_end_date: date
    addendum_status: AddendumStatus = AddendumStatus.pending
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_uploaded_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # enriched
    parent_contract_no: Optional[str] = None
    person_name: Optional[str] = None

    class Config:
        from_attributes = True


class ContractAddendumListResponse(BaseModel):
    """附約列表回應"""
    data: list[ContractAddendumResponse] = []
