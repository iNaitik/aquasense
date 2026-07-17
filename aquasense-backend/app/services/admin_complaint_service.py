"""Authority complaint management service layer.

Business logic for listing, inspecting, updating, and summarising complaints
from the authority/admin perspective.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.services.notification_service import send_complaint_notification

logger = logging.getLogger(__name__)

from app.models.complaint import Complaint, ComplaintStatus, IssueType
from app.models.complaint_status_history import ComplaintStatusHistory
from app.schemas.admin_complaint import (
    AdminComplaintDetail,
    AdminComplaintListItem,
    AdminComplaintListResponse,
    ComplaintStatsResponse,
    ComplaintStatusUpdateResponse,
    MatchedPipelineInfo,
)
from app.schemas.complaint import (
    ComplaintStatus as SchemaStatus,
    ComplaintStatusEvent,
)

# Ordered lifecycle – used to enforce forward-only transitions.
_STATUS_ORDER: list[str] = ["submitted", "reviewed", "assigned", "resolved"]

_STATUS_LABELS: dict[str, str] = {
    "submitted": "Submitted",
    "reviewed": "Reviewed",
    "assigned": "Assigned",
    "resolved": "Resolved",
}


# ---- List ----


def list_complaints(
    db: Session,
    *,
    current_status: Optional[str] = None,
    issue_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> AdminComplaintListResponse:
    """Return a paginated, filtered list of complaints ordered newest-first."""
    query = db.query(Complaint)

    if current_status is not None:
        query = query.filter(Complaint.current_status == ComplaintStatus(current_status))

    if issue_type is not None:
        query = query.filter(Complaint.issue_type == IssueType(issue_type))

    total = query.count()
    complaints = (
        query.order_by(Complaint.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [AdminComplaintListItem.model_validate(c) for c in complaints]
    return AdminComplaintListResponse.build(items, total, page, page_size)


# ---- Detail ----


def get_complaint_detail(
    db: Session, reference_id: str
) -> AdminComplaintDetail | None:
    """Return full complaint detail with real status history timeline."""
    complaint: Complaint | None = (
        db.query(Complaint)
        .filter(Complaint.reference_id == reference_id.upper())
        .first()
    )
    if complaint is None:
        return None

    timeline = _build_timeline(db, complaint)

    matched_pipeline_info = None
    if complaint.matched_pipeline is not None:
        matched_pipeline_info = MatchedPipelineInfo(
            pipeline_id=complaint.matched_pipeline.pipeline_id,
            distance_m=complaint.pipeline_distance_m,
        )

    return AdminComplaintDetail(
        reference_id=complaint.reference_id,
        issue_type=complaint.issue_type.value,
        description=complaint.description,
        latitude=complaint.latitude,
        longitude=complaint.longitude,
        address=complaint.address,
        image_url=complaint.image_url,
        current_status=complaint.current_status.value,
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
        timeline=timeline,
        matched_pipeline=matched_pipeline_info,
        citizen_name=complaint.citizen_name,
        phone_number=complaint.phone_number,
    )


# ---- Status update ----


class StatusTransitionError(Exception):
    """Raised when a status transition is invalid."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def update_complaint_status(
    db: Session, reference_id: str, new_status_str: str
) -> ComplaintStatusUpdateResponse:
    """Transition a complaint to a new status with forward-only enforcement.

    Raises:
        LookupError: complaint not found
        StatusTransitionError: invalid transition
    """
    complaint: Complaint | None = (
        db.query(Complaint)
        .filter(Complaint.reference_id == reference_id.upper())
        .first()
    )
    if complaint is None:
        raise LookupError(f"Complaint '{reference_id}' not found")

    new_status = ComplaintStatus(new_status_str)
    current_status = complaint.current_status

    # Same status – graceful no-op
    if current_status == new_status:
        return ComplaintStatusUpdateResponse(
            reference_id=complaint.reference_id,
            previous_status=current_status.value,
            current_status=current_status.value,
            updated_at=complaint.updated_at,
        )

    # Enforce forward-only progression
    current_idx = _STATUS_ORDER.index(current_status.value)
    new_idx = _STATUS_ORDER.index(new_status.value)

    if new_idx <= current_idx:
        raise StatusTransitionError(
            f"Cannot transition from '{current_status.value}' to '{new_status.value}'. "
            f"Backward transitions are not allowed."
        )

    if new_idx != current_idx + 1:
        raise StatusTransitionError(
            f"Cannot skip from '{current_status.value}' to '{new_status.value}'. "
            f"The next allowed status is '{_STATUS_ORDER[current_idx + 1]}'."
        )

    # Perform the transition in a single transaction
    previous_status = current_status
    complaint.current_status = new_status

    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status=new_status,
        note=None,
    )
    db.add(history)

    try:
        db.commit()
        db.refresh(complaint)
    except Exception:
        db.rollback()
        raise

    # Trigger status update SMS notification – failure-isolated from primary transaction
    event_map = {
        ComplaintStatus.reviewed: ("complaint_reviewed", f"Your AQUA-SENSE complaint {complaint.reference_id} is now under review."),
        ComplaintStatus.assigned: ("complaint_assigned", f"Your AQUA-SENSE complaint {complaint.reference_id} has been assigned for action."),
        ComplaintStatus.resolved: ("complaint_resolved", f"Your AQUA-SENSE complaint {complaint.reference_id} has been marked as resolved."),
    }
    if new_status in event_map:
        event_type, msg = event_map[new_status]
        try:
            send_complaint_notification(
                db,
                complaint,
                event_type=event_type,
                message=msg,
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error(
                f"Error generating {event_type} notification for {complaint.reference_id}: {exc}",
                exc_info=True,
            )

    return ComplaintStatusUpdateResponse(
        reference_id=complaint.reference_id,
        previous_status=previous_status.value,
        current_status=complaint.current_status.value,
        updated_at=complaint.updated_at,
    )


# ---- Stats ----


def get_complaint_stats(db: Session) -> ComplaintStatsResponse:
    """Return dynamic complaint counts grouped by status."""
    total = db.query(func.count(Complaint.id)).scalar() or 0

    counts_query = (
        db.query(Complaint.current_status, func.count(Complaint.id))
        .group_by(Complaint.current_status)
        .all()
    )

    counts: dict[str, int] = {s: 0 for s in _STATUS_ORDER}
    for status, count in counts_query:
        counts[status.value] = count

    resolved = counts.get("resolved", 0)
    return ComplaintStatsResponse(
        total_complaints=total,
        submitted=counts.get("submitted", 0),
        reviewed=counts.get("reviewed", 0),
        assigned=counts.get("assigned", 0),
        resolved=resolved,
        open_complaints=total - resolved,
    )


# ---- Timeline builder ----


def _build_timeline(db: Session, complaint: Complaint) -> list[ComplaintStatusEvent]:
    """Build the complaint timeline from real status history records.

    Falls back to a skeleton timeline for backwards compatibility when no
    history records exist (pre-existing complaints).
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
    current_idx = _STATUS_ORDER.index(complaint.current_status.value)

    for idx, status_value in enumerate(_STATUS_ORDER):
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
