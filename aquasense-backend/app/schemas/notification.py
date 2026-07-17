"""Pydantic schemas for SMS notification history / metadata."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.notification import Notification
from app.utils.phone import mask_phone_number


class NotificationMetadata(BaseModel):
    """Safe metadata representation of a sent or pending SMS notification.

    Never exposes unmasked phone numbers to prevent accidental privacy leakage.
    """

    id: int
    complaint_id: int
    channel: str
    event_type: str
    status: str
    provider: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    masked_recipient: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, n: Notification) -> "NotificationMetadata":
        return cls(
            id=n.id,
            complaint_id=n.complaint_id,
            channel=n.channel,
            event_type=n.event_type,
            status=n.status,
            provider=n.provider,
            created_at=n.created_at,
            sent_at=n.sent_at,
            masked_recipient=mask_phone_number(n.recipient),
        )
