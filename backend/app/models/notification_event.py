from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class NotificationEventType(str, Enum):
    # 合約
    CONTRACT_ACTIVATED = "contract.activated"
    CONTRACT_CONVERTED = "contract.converted"
    CONTRACT_TERMINATED = "contract.terminated"

    # 預約
    BOOKING_CONFIRMED = "booking.confirmed"
    BOOKING_CANCELLED = "booking.cancelled"


@dataclass
class NotificationEvent:
    event_type: NotificationEventType
    triggered_by: str
    recipients: list[str]
    data: dict = field(default_factory=dict)
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None
