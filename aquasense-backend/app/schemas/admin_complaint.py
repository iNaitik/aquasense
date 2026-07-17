"""Pydantic schemas for the Authority Complaint Management APIs.

These schemas are used by the /api/v1/admin/complaints endpoints.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.complaint import ComplaintStatus, ComplaintStatusEvent, IssueType


# ---- List endpoint ----


class AdminComplaintListItem(BaseModel):
    """Single complaint item returned in paginated list responses."""

    reference_id: str
    issue_type: IssueType
    description: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    current_status: ComplaintStatus
    created_at: datetime
    updated_at: datetime
    citizen_name: Optional[str] = None
    phone_number: Optional[str] = None

    @field_validator("phone_number", mode="after")
    @classmethod
    def mask_phone_number(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        if len(v) > 7:
            return v[:3] + "*" * (len(v) - 7) + v[-4:]
        return v

    model_config = ConfigDict(from_attributes=True)


class AdminComplaintListResponse(BaseModel):
    """Paginated wrapper for authority complaint listings."""

    items: list[AdminComplaintListItem]
    total: int
    page: int
    page_size: int
    total_pages: int

    @staticmethod
    def build(
        items: list[AdminComplaintListItem],
        total: int,
        page: int,
        page_size: int,
    ) -> "AdminComplaintListResponse":
        return AdminComplaintListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, math.ceil(total / page_size)),
        )


# ---- Detail endpoint ----


class MatchedPipelineInfo(BaseModel):
    """Information about the simulated pipeline segment matched to this complaint."""

    pipeline_id: str
    distance_m: Optional[float] = None


class AdminComplaintDetail(BaseModel):
    """Full complaint details for the authority inspection view."""

    reference_id: str
    issue_type: IssueType
    description: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    current_status: ComplaintStatus
    created_at: datetime
    updated_at: datetime
    timeline: list[ComplaintStatusEvent]
    matched_pipeline: Optional[MatchedPipelineInfo] = None
    citizen_name: Optional[str] = None
    phone_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ---- Status update ----


class ComplaintStatusUpdateRequest(BaseModel):
    """Request body for PATCH status endpoint."""

    status: ComplaintStatus


class ComplaintStatusUpdateResponse(BaseModel):
    """Response after a successful status transition."""

    reference_id: str
    previous_status: ComplaintStatus
    current_status: ComplaintStatus
    updated_at: datetime


# ---- Summary stats ----


class ComplaintStatsResponse(BaseModel):
    """Aggregate complaint statistics for the authority dashboard."""

    total_complaints: int
    submitted: int = 0
    reviewed: int = 0
    assigned: int = 0
    resolved: int = 0
    open_complaints: int = Field(
        0, description="All complaints not currently resolved"
    )
