"""Complaint ORM model."""

import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class IssueType(str, enum.Enum):
    """Supported issue types – must match the frontend exactly."""

    water_leakage = "water_leakage"
    low_pressure = "low_pressure"
    discolored_water = "discolored_water"
    unusual_flow = "unusual_flow"
    other = "other"


class ComplaintStatus(str, enum.Enum):
    """Complaint lifecycle statuses – must match the frontend exactly."""

    submitted = "submitted"
    reviewed = "reviewed"
    assigned = "assigned"
    resolved = "resolved"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reference_id = Column(String(20), unique=True, nullable=False, index=True)
    citizen_name = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    issue_type = Column(Enum(IssueType, name="issue_type_enum"), nullable=False)
    description = Column(Text, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    matched_pipeline_id = Column(
        Integer,
        ForeignKey("pipelines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pipeline_distance_m = Column(Float, nullable=True)
    matched_pipeline = relationship("Pipeline", backref="complaints")
    current_status = Column(
        Enum(ComplaintStatus, name="complaint_status_enum"),
        nullable=False,
        default=ComplaintStatus.submitted,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
