"""Complaint business logic – reference generation and persistence."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import os
import shutil
import uuid

from fastapi import UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.complaint import Complaint, ComplaintStatus, IssueType as ModelIssueType
from app.models.complaint_status_history import ComplaintStatusHistory
from app.schemas.complaint import (
    ComplaintDetail,
    ComplaintStatus as SchemaStatus,
    ComplaintStatusEvent,
    CreateComplaintRequest,
    CreateComplaintResponse,
)
from app.services.pipeline_matching_service import find_nearest_pipeline
from app.services.pipeline_recalculation_service import recalculate_pipeline_risk_from_complaints
from app.services.notification_service import send_complaint_notification

logger = logging.getLogger(__name__)


# ---- Status label map (for the timeline) ----

_STATUS_LABELS: dict[str, str] = {
    "submitted": "Submitted",
    "reviewed": "Reviewed",
    "assigned": "Assigned",
    "resolved": "Resolved",
}

# Ordered lifecycle so we can generate the full timeline skeleton.
_STATUS_ORDER: list[str] = ["submitted", "reviewed", "assigned", "resolved"]


# ---- Reference ID generation ----

def _generate_reference_id(db: Session) -> str:
    """Generate a unique reference ID in the format AQS-YYYY-XXXX.

    Uses a DB query to find the current max sequence number for the year,
    then increments it. Safe enough for a prototype with low concurrency.
    """
    year = datetime.now(timezone.utc).year
    prefix = f"AQS-{year}-"

    # Find the highest existing sequence number for this year.
    result = db.query(func.max(Complaint.reference_id)).filter(
        Complaint.reference_id.like(f"{prefix}%")
    ).scalar()

    if result:
        try:
            last_seq = int(result.split("-")[-1])
        except (ValueError, IndexError):
            last_seq = 0
    else:
        last_seq = 0

    next_seq = last_seq + 1
    return f"{prefix}{next_seq:04d}"


# ---- Service functions ----

def create_complaint(
    db: Session,
    payload: CreateComplaintRequest,
    photo: UploadFile | None = None,
) -> CreateComplaintResponse:
    """Persist a new complaint and return the public reference."""
    reference_id = _generate_reference_id(db)

    image_url: str | None = None
    if photo and photo.filename:
        os.makedirs("uploads", exist_ok=True)
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        safe_name = f"{reference_id.lower()}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join("uploads", safe_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        image_url = f"/uploads/{safe_name}"

    complaint = Complaint(
        reference_id=reference_id,
        citizen_name=payload.citizen_name,
        phone_number=payload.phone_number,
        issue_type=ModelIssueType(payload.issue_type.value),
        description=payload.description,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
        image_url=image_url,
        current_status=ComplaintStatus.submitted,
    )

    db.add(complaint)
    db.flush()  # flush to get complaint.id before creating history

    # Create the initial "submitted" history event
    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status=ComplaintStatus.submitted,
        note=None,
    )
    db.add(history)
    db.flush()

    # Find nearest pipeline and link if within threshold
    try:
        with db.begin_nested():
            match_result = find_nearest_pipeline(
                db,
                latitude=complaint.latitude,
                longitude=complaint.longitude,
            )
            if match_result is not None:
                matched_pipe, distance_m = match_result
                complaint.matched_pipeline_id = matched_pipe.id
                complaint.pipeline_distance_m = distance_m
                db.flush()

                # Recalculate rolling features and prediction
                recalculate_pipeline_risk_from_complaints(db, matched_pipe)
    except Exception as e:
        logger.error(
            f"Failed to match pipeline or recalculate risk for complaint {complaint.reference_id}: {e}",
            exc_info=True,
        )

    db.commit()
    db.refresh(complaint)

    # Trigger SMS notification – failure-isolated from the primary complaint transaction
    try:
        msg = f"Your AQUA-SENSE complaint {complaint.reference_id} has been submitted successfully. You can use this reference number to track your complaint."
        send_complaint_notification(
            db,
            complaint,
            event_type="complaint_submitted",
            message=msg,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(
            f"Error generating complaint_submitted notification for {complaint.reference_id}: {exc}",
            exc_info=True,
        )

    return CreateComplaintResponse(
        reference_id=complaint.reference_id,
        created_at=complaint.created_at,
    )


def get_complaint_by_reference(db: Session, reference_id: str) -> ComplaintDetail | None:
    """Look up a complaint by its public reference ID.

    Returns *None* if not found so the route can raise 404.
    """
    complaint: Complaint | None = (
        db.query(Complaint)
        .filter(Complaint.reference_id == reference_id.upper())
        .first()
    )

    if complaint is None:
        return None

    # Build the timeline from real history records (with fallback)
    timeline = _build_timeline(db, complaint)

    return ComplaintDetail(
        reference_id=complaint.reference_id,
        issue_type=complaint.issue_type.value,
        description=complaint.description,
        address=complaint.address,
        image_url=complaint.image_url,
        current_status=complaint.current_status.value,
        timeline=timeline,
    )


def _build_timeline(db: Session, complaint: Complaint) -> list[ComplaintStatusEvent]:
    """Build the complaint timeline from real status history records.

    Falls back to a skeleton timeline for backwards compatibility when no
    history records exist (pre-existing complaints created before the
    status history table was added).
    """
    history_records = (
        db.query(ComplaintStatusHistory)
        .filter(ComplaintStatusHistory.complaint_id == complaint.id)
        .order_by(ComplaintStatusHistory.created_at.asc())
        .all()
    )

    # Build a lookup of status → (timestamp, note) from real history
    status_data: dict[str, tuple[datetime | None, str | None]] = {}
    for record in history_records:
        status_val = record.status.value if hasattr(record.status, 'value') else str(record.status)
        status_data[status_val] = (record.created_at, record.note)

    # Ensure submitted always has a timestamp (from created_at if missing)
    if "submitted" not in status_data:
        status_data["submitted"] = (complaint.created_at, None)

    timeline: list[ComplaintStatusEvent] = []
    for status_value in _STATUS_ORDER:
        ts, note = status_data.get(status_value, (None, None))

        timeline.append(
            ComplaintStatusEvent(
                status=SchemaStatus(status_value),
                label=_STATUS_LABELS[status_value],
                timestamp=ts,
                note=note,
            )
        )

    return timeline
