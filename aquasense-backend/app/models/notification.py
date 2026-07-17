"""Notification ORM model."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import backref, relationship

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(
        Integer,
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel = Column(String(20), default="sms", nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    recipient = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    provider = Column(String(50), nullable=True)
    provider_message_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sent_at = Column(DateTime(timezone=True), nullable=True)

    complaint = relationship(
        "Complaint",
        backref=backref("notifications", cascade="all, delete-orphan", passive_deletes=True),
    )

    __table_args__ = (
        UniqueConstraint(
            "complaint_id", "event_type", name="uq_notification_complaint_event"
        ),
    )
