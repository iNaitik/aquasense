"""Geographic pipeline matching service using equirectangular segment distance approximation."""

from __future__ import annotations

import math
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.pipeline import Pipeline


def _calculate_segment_distance_m(
    lat0: float,
    lon0: float,
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate approximate shortest distance in meters from point (lat0, lon0) to segment (lat1, lon1)-(lat2, lon2).

    Uses equirectangular projection centered around point P (lat0, lon0). For small geographic
    regions like Indore (~22.7 N), this approximation is fast and accurate.
    """
    R = 6371000.0  # Earth radius in meters
    lat0_rad = math.radians(lat0)
    cos_lat0 = math.cos(lat0_rad)

    # Convert point 1 (start) to local meters relative to (lat0, lon0)
    x1 = (lon1 - lon0) * (math.pi / 180.0) * R * cos_lat0
    y1 = (lat1 - lat0) * (math.pi / 180.0) * R

    # Convert point 2 (end) to local meters relative to (lat0, lon0)
    x2 = (lon2 - lon0) * (math.pi / 180.0) * R * cos_lat0
    y2 = (lat2 - lat0) * (math.pi / 180.0) * R

    dx = x2 - x1
    dy = y2 - y1
    len_sq = dx * dx + dy * dy

    if len_sq == 0.0:
        # Segment is a single point
        return math.sqrt(x1 * x1 + y1 * y1)

    # Project vector from point 1 to origin (-x1, -y1) onto segment vector (dx, dy)
    t = (-x1 * dx + -y1 * dy) / len_sq
    t_clamped = max(0.0, min(1.0, t))

    x_closest = x1 + t_clamped * dx
    y_closest = y1 + t_clamped * dy

    return math.sqrt(x_closest * x_closest + y_closest * y_closest)


def find_nearest_pipeline(
    db: Session,
    latitude: Optional[float],
    longitude: Optional[float],
    max_distance_m: Optional[float] = None,
) -> Optional[Tuple[Pipeline, float]]:
    """Find the nearest pipeline segment to the given latitude and longitude within max_distance_m.

    Returns:
        A tuple of (matched_pipeline, distance_in_meters) if found within max_distance_m, else None.
    """
    if latitude is None or longitude is None:
        return None

    if max_distance_m is None:
        max_distance_m = settings.PIPELINE_MATCH_MAX_DISTANCE_M

    pipelines = db.query(Pipeline).all()
    if not pipelines:
        return None

    best_pipeline: Optional[Pipeline] = None
    best_distance: float = float("inf")

    for pipe in pipelines:
        dist = _calculate_segment_distance_m(
            lat0=latitude,
            lon0=longitude,
            lat1=pipe.start_latitude,
            lon1=pipe.start_longitude,
            lat2=pipe.end_latitude,
            lon2=pipe.end_longitude,
        )
        if dist < best_distance:
            best_distance = dist
            best_pipeline = pipe

    if best_pipeline is not None and best_distance <= max_distance_m:
        return (best_pipeline, round(best_distance, 2))

    return None
