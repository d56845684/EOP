from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime, date, time
import calendar


def _add_months(d: date, months: int) -> date:
    """日期加上指定月數，處理月底天數差異"""
    year = d.year
    month = d.month + months
    if month > 12:
        year += (month - 1) // 12
        month = (month - 1) % 12 + 1
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, max_day))


class TeacherSlotBase(BaseModel):
    teacher_id: str = Field(..., description="教師 ID")
    teacher_contract_id: Optional[str] = Field(None, description="教師合約 ID")
    slot_date: date = Field(..., description="時段日期")
    start_time: time = Field(..., description="開始時間")
    end_time: time = Field(..., description="結束時間")
    is_available: bool = Field(True, description="是否可預約")
    notes: Optional[str] = Field(None, description="備註")


class TeacherSlotCreate(TeacherSlotBase):
    """建立教師時段的請求，時段日期不得超過今天起三個月"""

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "teacher_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "slot_date": "2026-05-01",
                "start_time": "09:00:00",
                "end_time": "12:00:00",
                "is_available": True,
            }]
        }
    }

    @model_validator(mode="after")
    def validate_slot_date(self):
        today = date.today()
        max_date = _add_months(today, 3)
        if self.slot_date > max_date:
            raise ValueError("時段日期不得超過三個月內")
        return self


class TeacherSlotBatchCreate(BaseModel):
    """批次建立教師時段的請求（週期性），日期範圍不得超過三個月"""
    teacher_id: str = Field(..., description="教師 ID")
    teacher_contract_id: Optional[str] = Field(None, description="教師合約 ID")
    start_date: date = Field(..., description="開始日期")
    end_date: date = Field(..., description="結束日期")
    weekdays: List[int] = Field(..., description="星期幾（0=週一, 6=週日）")
    start_time: time = Field(..., description="開始時間")
    end_time: time = Field(..., description="結束時間")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "teacher_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "start_date": "2026-04-14",
                "end_date": "2026-06-30",
                "weekdays": [0, 2, 4],
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "notes": "每週一三五上午固定時段",
            }]
        }
    }

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date < self.start_date:
            raise ValueError("結束日期不得早於開始日期")

        max_end_date = _add_months(self.start_date, 3)
        if self.end_date > max_end_date:
            raise ValueError("批次建立時段日期範圍不得超過三個月")
        return self


class TeacherSlotBatchDelete(BaseModel):
    """批次刪除教師時段的請求"""
    teacher_id: str = Field(..., description="教師 ID")
    start_date: date = Field(..., description="開始日期")
    end_date: date = Field(..., description="結束日期")
    weekdays: Optional[List[int]] = Field(None, description="星期幾（0=週一, 6=週日），不填則全部")
    start_time: Optional[time] = Field(None, description="開始時間，篩選特定時段")
    end_time: Optional[time] = Field(None, description="結束時間，篩選特定時段")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "teacher_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
                "weekdays": [0, 2, 4],
            }]
        }
    }


class TeacherSlotBatchUpdate(BaseModel):
    """批次更新教師時段的請求"""
    # 篩選條件
    teacher_id: str = Field(..., description="教師 ID")
    start_date: date = Field(..., description="開始日期")
    end_date: date = Field(..., description="結束日期")
    weekdays: Optional[List[int]] = Field(None, description="星期幾（0=週一, 6=週日），不填則全部")
    filter_start_time: Optional[time] = Field(None, description="篩選開始時間")
    filter_end_time: Optional[time] = Field(None, description="篩選結束時間")
    # 更新內容
    new_start_time: Optional[time] = Field(None, description="新開始時間")
    new_end_time: Optional[time] = Field(None, description="新結束時間")
    is_available: Optional[bool] = Field(None, description="是否可預約")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "teacher_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "start_date": "2026-04-14",
                "end_date": "2026-04-30",
                "weekdays": [1, 3],
                "is_available": False,
                "notes": "批次關閉週二四時段",
            }]
        }
    }


class TeacherSlotBatchDeleteByIds(BaseModel):
    """根據 ID 批次刪除教師時段"""
    slot_ids: List[str] = Field(..., description="時段 ID 列表")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "slot_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890", "b2c3d4e5-f6a7-8901-bcde-f12345678901"],
            }]
        }
    }


class TeacherSlotBatchUpdateByIds(BaseModel):
    """根據 ID 批次更新教師時段"""
    slot_ids: List[str] = Field(..., description="時段 ID 列表")
    # 更新內容
    new_start_time: Optional[time] = Field(None, description="新開始時間")
    new_end_time: Optional[time] = Field(None, description="新結束時間")
    is_available: Optional[bool] = Field(None, description="是否可預約")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "slot_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
                "is_available": False,
                "notes": "批次關閉時段",
            }]
        }
    }


class TeacherSlotUpdate(BaseModel):
    """更新教師時段的請求"""
    teacher_contract_id: Optional[str] = Field(None, description="教師合約 ID")
    slot_date: Optional[date] = Field(None, description="時段日期")
    start_time: Optional[time] = Field(None, description="開始時間")
    end_time: Optional[time] = Field(None, description="結束時間")
    is_available: Optional[bool] = Field(None, description="是否可預約")
    notes: Optional[str] = Field(None, description="備註")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "is_available": True,
                "notes": "調整為下午時段",
            }]
        }
    }


class TeacherSlotResponse(BaseModel):
    """教師時段回應"""
    id: str
    teacher_id: str
    teacher_contract_id: Optional[str] = None
    slot_date: date
    start_time: time
    end_time: time
    is_available: bool
    is_booked: bool
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 關聯資料
    teacher_name: Optional[str] = None
    teacher_no: Optional[str] = None
    teacher_contract_no: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [{
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "teacher_id": "660e8400-e29b-41d4-a716-446655440000",
                "teacher_contract_id": "770e8400-e29b-41d4-a716-446655440000",
                "slot_date": "2026-04-15",
                "start_time": "09:00:00",
                "end_time": "12:00:00",
                "is_available": True,
                "is_booked": False,
                "notes": None,
                "created_at": "2026-04-01T08:00:00",
                "updated_at": "2026-04-01T08:00:00",
                "teacher_name": "陳美玲",
                "teacher_no": "EOPT001",
                "teacher_contract_no": "TC-2026-001",
            }]
        }
    }


class TeacherSlotListResponse(BaseModel):
    """教師時段列表回應"""
    success: bool = True
    data: list[TeacherSlotResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
