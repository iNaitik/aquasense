"""Authority Complaint Management API endpoints.

TODO: These endpoints must be protected with authentication (JWT or similar)
      before any production deployment.  Currently unprotected for Prototype 1.

Prefix: /api/v1/admin/complaints
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.complaint import ComplaintStatus, IssueType
from app.schemas.admin_complaint import (
    AdminComplaintDetail,
    AdminComplaintListResponse,
    ComplaintStatsResponse,
    ComplaintStatusUpdateRequest,
    ComplaintStatusUpdateResponse,
)
from app.schemas.notification import NotificationMetadata
from app.models.complaint import Complaint
from app.models.notification import Notification
from app.services.admin_complaint_service import (
    StatusTransitionError,
    get_complaint_detail,
    get_complaint_stats,
    list_complaints,
    update_complaint_status,
)

from app.core.security import get_current_authority

# Valid enum values for validation
_VALID_STATUSES = {s.value for s in ComplaintStatus}
_VALID_ISSUE_TYPES = {t.value for t in IssueType}

router = APIRouter(
    prefix="/api/v1/admin/complaints",
    tags=["Authority Complaints"],
    dependencies=[Depends(get_current_authority)],
)


# ---- Stats (declared FIRST to avoid /{reference_id} capturing "stats") ----


@router.get(
    "/stats/summary",
    response_model=ComplaintStatsResponse,
    summary="Get aggregate complaint statistics",
    description=(
        "Returns total complaint count and per-status breakdown, calculated "
        "dynamically from PostgreSQL.\n\n"
        "**TODO:** Protect with authority authentication before production."
    ),
)
def get_stats_summary(db: Session = Depends(get_db)) -> ComplaintStatsResponse:
    return get_complaint_stats(db)


# ---- List ----


@router.get(
    "",
    response_model=AdminComplaintListResponse,
    summary="List complaints with filtering and pagination",
    description=(
        "Returns a paginated list of citizen complaints ordered newest-first.\n\n"
        "Supports optional filters: `current_status`, `issue_type`.\n"
        "Supports pagination: `page`, `page_size`.\n\n"
        "**TODO:** Protect with authority authentication before production."
    ),
)
def list_all_complaints(
    current_status: Optional[str] = Query(
        None, description="Filter by status: submitted, reviewed, assigned, resolved"
    ),
    issue_type: Optional[str] = Query(
        None, description="Filter by issue type: water_leakage, low_pressure, discolored_water, unusual_flow, other"
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db),
) -> AdminComplaintListResponse:
    # Validate filter values
    if current_status is not None:
        cs = current_status.strip().lower()
        if cs not in _VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid current_status '{current_status}'. "
                       f"Must be one of: {', '.join(sorted(_VALID_STATUSES))}.",
            )
        current_status = cs

    if issue_type is not None:
        it = issue_type.strip().lower()
        if it not in _VALID_ISSUE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid issue_type '{issue_type}'. "
                       f"Must be one of: {', '.join(sorted(_VALID_ISSUE_TYPES))}.",
            )
        issue_type = it

    return list_complaints(
        db,
        current_status=current_status,
        issue_type=issue_type,
        page=page,
        page_size=page_size,
    )


# ---- Detail ----


@router.get(
    "/{reference_id}",
    response_model=AdminComplaintDetail,
    summary="Get detailed complaint information",
    description=(
        "Returns full complaint details including real status history timeline.\n\n"
        "**TODO:** Protect with authority authentication before production."
    ),
)
def get_complaint_by_reference(
    reference_id: str, db: Session = Depends(get_db)
) -> AdminComplaintDetail:
    result = get_complaint_detail(db, reference_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint '{reference_id}' not found.",
        )
    return result


# ---- Notifications History ----


@router.get(
    "/{reference_id}/notifications",
    response_model=list[NotificationMetadata],
    summary="Get notification history for a complaint",
    description="Returns all sent/failed/pending SMS notifications for this complaint with masked recipient phone numbers.",
)
def get_complaint_notifications(
    reference_id: str, db: Session = Depends(get_db)
) -> list[NotificationMetadata]:
    complaint: Complaint | None = (
        db.query(Complaint)
        .filter(Complaint.reference_id == reference_id.upper())
        .first()
    )
    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint '{reference_id}' not found.",
        )

    notifications = (
        db.query(Notification)
        .filter(Notification.complaint_id == complaint.id)
        .order_by(Notification.created_at.asc())
        .all()
    )
    return [NotificationMetadata.from_orm_model(n) for n in notifications]


# ---- Status update ----


@router.patch(
    "/{reference_id}/status",
    response_model=ComplaintStatusUpdateResponse,
    summary="Update complaint status (forward-only)",
    description=(
        "Transitions a complaint to the next status in the lifecycle.\n\n"
        "Allowed forward transitions:\n"
        "- submitted → reviewed\n"
        "- reviewed → assigned\n"
        "- assigned → resolved\n\n"
        "Backward transitions and stage-skipping are rejected.\n\n"
        "**TODO:** Protect with authority authentication before production."
    ),
)
def update_status(
    reference_id: str,
    body: ComplaintStatusUpdateRequest,
    db: Session = Depends(get_db),
) -> ComplaintStatusUpdateResponse:
    try:
        return update_complaint_status(db, reference_id, body.status.value)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint '{reference_id}' not found.",
        )
    except StatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
