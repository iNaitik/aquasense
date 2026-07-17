"""ComplaintStatusHistory ORM model – tracks every status transition for a complaint."""

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import backref, relationship

from app.database import Base
from app.models.complaint import ComplaintStatus


class ComplaintStatusHistory(Base):
    """Persists each status transition so the citizen timeline and authority
    audit trail reflect real events with accurate timestamps.
    """

    __tablename__ = "complaint_status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(
        Integer,
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(ComplaintStatus, name="complaint_status_enum", create_type=False),
        nullable=False,
    )
    note = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship back to Complaint (with cascade for ORM deletes)
    complaint = relationship(
        "Complaint",
        backref=backref("status_history", cascade="all, delete-orphan", passive_deletes=True),
    )
