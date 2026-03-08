from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime, date, time
from enum import Enum
import calendar


class BookingStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"


class BookingBase(BaseModel):
    student_id: str = Field(..., description="學生 ID")
    teacher_id: str = Field(..., description="教師 ID")
    course_id: str = Field(..., description="課程 ID")
    student_contract_id: Optional[str] = Field(None, description="學生合約 ID（試上學生可不提供）")
    teacher_contract_id: Optional[str] = Field(None, description="教師合約 ID")
    teacher_slot_id: Optional[str] = Field(None, description="教師時段 ID（可選，系統會自動尋找）")
    booking_date: date = Field(..., description="預約日期")
    start_time: time = Field(..., description="開始時間")
    end_time: time = Field(..., description="結束時間")
    notes: Optional[str] = Field(None, description="備註")

    @model_validator(mode="after")
    def validate_30min_boundary(self):
        """驗證時間必須在 30 分鐘邊界上"""
        # 分鐘必須為 0 或 30，秒必須為 0
        if self.start_time.minute not in (0, 30) or self.start_time.second != 0:
            raise ValueError("開始時間必須在 30 分鐘邊界上（例如 14:00 或 14:30）")
        if self.end_time.minute not in (0, 30) or self.end_time.second != 0:
            raise ValueError("結束時間必須在 30 分鐘邊界上（例如 15:00 或 15:30）")

        # end_time > start_time
        if self.end_time <= self.start_time:
            raise ValueError("結束時間必須晚於開始時間")

        # 時長至少 30 分鐘且為 30 的倍數
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        duration = end_minutes - start_minutes
        if duration < 30:
            raise ValueError("預約時長至少 30 分鐘")
        if duration % 30 != 0:
            raise ValueError("預約時長必須為 30 分鐘的倍數")

        return self


class BookingCreate(BookingBase):
    """建立預約的請求

    teacher_slot_id 為可選：
    - 如果提供：驗證預約時間是否落在該時段區間內
    - 如果不提供：自動尋找包含預約時間的可用時段
    """
    pass


class BookingUpdate(BaseModel):
    """更新預約的請求"""
    booking_status: Optional[BookingStatus] = Field(None, description="預約狀態")
    end_time: Optional[time] = Field(None, description="結束時間（僅允許縮短預約）")
    notes: Optional[str] = Field(None, description="備註")


class BookingResponse(BaseModel):
    """預約回應"""
    id: str
    booking_no: str
    student_id: str
    teacher_id: str
    course_id: str
    student_contract_id: Optional[str] = None
    teacher_contract_id: Optional[str] = None
    teacher_slot_id: str
    teacher_hourly_rate: float
    teacher_rate_percentage: Optional[float] = None
    booking_status: BookingStatus
    booking_date: date
    start_time: time
    end_time: time
    booking_type: str = "regular"
    is_trial_to_formal: bool = False
    lessons_used: int = 1
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 關聯資料
    student_name: Optional[str] = None
    teacher_name: Optional[str] = None
    course_name: Optional[str] = None
    student_contract_no: Optional[str] = None
    teacher_contract_no: Optional[str] = None

    class Config:
        from_attributes = True


class BookingListResponse(BaseModel):
    """預約列表回應"""
    success: bool = True
    data: list[BookingResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0


class BookingBatchUpdateByIds(BaseModel):
    """根據 ID 批次更新預約狀態"""
    booking_ids: List[str] = Field(..., description="預約 ID 列表")
    booking_status: BookingStatus = Field(..., description="新狀態")
    notes: Optional[str] = Field(None, description="備註")


class BookingBatchDeleteByIds(BaseModel):
    """根據 ID 批次刪除預約"""
    booking_ids: List[str] = Field(..., description="預約 ID 列表")


class BookingBatchUpdate(BaseModel):
    """批次更新預約（週期性篩選）"""
    # 篩選條件
    start_date: date = Field(..., description="開始日期")
    end_date: date = Field(..., description="結束日期")
    weekdays: Optional[List[int]] = Field(None, description="星期幾（0=週一, 6=週日），不填則全部")
    student_id: Optional[str] = Field(None, description="篩選學生")
    teacher_id: Optional[str] = Field(None, description="篩選教師")
    course_id: Optional[str] = Field(None, description="篩選課程")
    filter_status: Optional[BookingStatus] = Field(None, description="篩選狀態")
    # 更新內容
    new_status: BookingStatus = Field(..., description="新狀態")
    notes: Optional[str] = Field(None, description="備註")


class BookingBatchDelete(BaseModel):
    """批次刪除預約（週期性篩選）"""
    start_date: date = Field(..., description="開始日期")
    end_date: date = Field(..., description="結束日期")
    weekdays: Optional[List[int]] = Field(None, description="星期幾（0=週一, 6=週日），不填則全部")
    student_id: Optional[str] = Field(None, description="篩選學生")
    teacher_id: Optional[str] = Field(None, description="篩選教師")
    course_id: Optional[str] = Field(None, description="篩選課程")
    filter_status: Optional[BookingStatus] = Field(None, description="篩選狀態")


class BookingBatchCreate(BaseModel):
    """批次建立預約（週期性），日期範圍不得超過三個月"""
    student_id: str = Field(..., description="學生 ID")
    student_contract_id: Optional[str] = Field(None, description="學生合約 ID（試上學生可不提供）")
    course_id: Optional[str] = Field(None, description="課程 ID（試上學生無合約時必填）")
    teacher_id: str = Field(..., description="教師 ID")
    teacher_contract_id: Optional[str] = Field(None, description="教師合約 ID（可選）")
    start_date: date = Field(..., description="開始日期")
    end_date: date = Field(..., description="結束日期")
    weekdays: List[int] = Field(..., description="星期幾（0=週一, 6=週日）")
    start_time: Optional[time] = Field(None, description="篩選開始時間（可選）")
    end_time: Optional[time] = Field(None, description="篩選結束時間（可選）")
    notes: Optional[str] = Field(None, description="備註")

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date < self.start_date:
            raise ValueError("結束日期不得早於開始日期")

        # 計算 start_date + 3 個月
        year = self.start_date.year
        month = self.start_date.month + 3
        if month > 12:
            year += (month - 1) // 12
            month = (month - 1) % 12 + 1
        max_day = calendar.monthrange(year, month)[1]
        day = min(self.start_date.day, max_day)
        max_end_date = date(year, month, day)

        if self.end_date > max_end_date:
            raise ValueError("批次預約日期範圍不得超過三個月")

        return self


class TimeBlock(BaseModel):
    """30 分鐘時間區塊"""
    start_time: time
    end_time: time
    is_available: bool = True
    booking_id: Optional[str] = None


class SlotAvailabilityResponse(BaseModel):
    """時段可用性回應"""
    slot_id: str
    slot_date: date
    slot_start_time: time
    slot_end_time: time
    blocks: List[TimeBlock] = []
