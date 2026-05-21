from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


GOOGLE_DOC_PREFIX = "https://docs.google.com/"


class LessonNoteUploadRequest(BaseModel):
    google_doc_url: str = Field(..., description="Google Doc URL（必須以 https://docs.google.com/ 開頭）")

    @field_validator("google_doc_url")
    @classmethod
    def validate_google_doc_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(GOOGLE_DOC_PREFIX):
            raise ValueError(f"必須是 Google Doc 連結（以 {GOOGLE_DOC_PREFIX} 開頭）")
        return v


class LessonNoteResponse(BaseModel):
    id: str
    booking_id: str
    google_doc_url: str
    status: str
    uploaded_by: str
    uploaded_at: datetime
    confirmed_by: Optional[str] = None
    confirmed_by_role: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
