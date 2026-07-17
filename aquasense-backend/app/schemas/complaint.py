"""Pydantic schemas for complaint API requests and responses."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from app.utils.phone import normalize_indian_phone


# ---- Enums (mirror the ORM / frontend) ----

class IssueType(str, Enum):
    water_leakage = "water_leakage"
    low_pressure = "low_pressure"
    discolored_water = "discolored_water"
    unusual_flow = "unusual_flow"
    other = "other"


class ComplaintStatus(str, Enum):
    submitted = "submitted"
    reviewed = "reviewed"
    assigned = "assigned"
    resolved = "resolved"


# ---- Request ----

class CreateComplaintRequest(BaseModel):
    citizen_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=10, max_length=20)
    issue_type: IssueType
    description: str = Field(..., min_length=10)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=500)

    @field_validator("citizen_name")
    @classmethod
    def validate_citizen_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed or len(trimmed) < 2:
            raise ValueError("citizen_name must not be empty and must be at least 2 characters.")
        return trimmed

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_indian_phone(v)

    @model_validator(mode="after")
    def require_location(self) -> "CreateComplaintRequest":
        has_coords = self.latitude is not None and self.longitude is not None
        has_address = self.address is not None and self.address.strip() != ""
        if not has_coords and not has_address:
            raise ValueError(
                "Either an address or coordinates (latitude + longitude) must be provided."
            )
        return self


# ---- Responses ----

class CreateComplaintResponse(BaseModel):
    reference_id: str
    created_at: datetime


class ComplaintStatusEvent(BaseModel):
    status: ComplaintStatus
    label: str
    timestamp: Optional[datetime] = None
    note: Optional[str] = None


class ComplaintDetail(BaseModel):
    reference_id: str
    issue_type: IssueType
    description: str
    address: Optional[str] = None
    image_url: Optional[str] = None
    current_status: ComplaintStatus
    timeline: list[ComplaintStatusEvent]
