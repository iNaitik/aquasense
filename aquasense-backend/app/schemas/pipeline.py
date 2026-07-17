"""Pydantic schemas for Pipeline API responses and summaries."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PipelineMapItem(BaseModel):
    """Lightweight schema for map rendering and geographic visualization."""
    pipeline_id: str
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    risk_score: float
    risk_level: str
    center_latitude: Optional[float] = None
    center_longitude: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class PipelineDetail(BaseModel):
    """Detailed schema for full pipeline inspection and attributes."""
    pipeline_id: str

    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    center_latitude: float
    center_longitude: float

    pipe_age_years: float
    material: str
    diameter_mm: float
    length_m: float

    previous_failures: int
    days_since_last_maintenance: float

    complaints_last_30_days: int
    leakage_complaints_30d: int

    failure_probability: float
    risk_score: float
    risk_level: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PipelineStatsSummary(BaseModel):
    """Aggregate summary statistics of the simulated Indore pipeline network."""
    total_pipelines: int
    risk_distribution: dict[str, int] = Field(..., json_schema_extra={"example": {"LOW": 385, "MEDIUM": 181, "HIGH": 184}})
    average_risk_score: float
