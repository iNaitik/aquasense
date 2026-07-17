"""Tests for Authority Complaint Management API endpoints.

Covers:
  - List all complaints, newest-first ordering, pagination
  - Filter by status, issue type, and combined filters
  - Complaint detail retrieval
  - Unknown complaint → 404
  - Forward status transitions (submitted → reviewed → assigned → resolved)
  - Backward and skip transitions are rejected
  - Invalid status value is rejected
  - Summary statistics return correct dynamic counts
  - Status history is created on transitions
  - Citizen tracking returns correct timeline

TODO: These tests run against the live development database.
      In a future iteration, use a test-specific database or transactions.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models.complaint import Complaint, ComplaintStatus, IssueType
from app.models.complaint_status_history import ComplaintStatusHistory

client = TestClient(app)


# ---- Helpers ----


def _create_test_complaint(db: Session, **overrides) -> Complaint:
    """Insert a complaint directly via ORM for test isolation."""
    from app.services.complaint_service import _generate_reference_id

    ref_id = overrides.pop("reference_id", None) or _generate_reference_id(db)
    defaults = dict(
        reference_id=ref_id,
        citizen_name="Test Citizen",
        phone_number="+919876543210",
        issue_type=IssueType.water_leakage,
        description="Test complaint for authority management unit tests",
        latitude=22.7196,
        longitude=75.8577,
        address="Test Address, Indore",
        current_status=ComplaintStatus.submitted,
    )
    defaults.update(overrides)
    complaint = Complaint(**defaults)
    db.add(complaint)
    db.flush()

    # Create initial submitted history
    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        status=ComplaintStatus.submitted,
    )
    db.add(history)
    db.commit()
    db.refresh(complaint)
    return complaint


@pytest.fixture(scope="module")
def test_complaints():
    """Create a set of test complaints with various statuses and issue types."""
    db = SessionLocal()
    created = []
    try:
        # Create complaints with different statuses
        for status in [ComplaintStatus.submitted, ComplaintStatus.reviewed,
                       ComplaintStatus.assigned, ComplaintStatus.resolved]:
            c = _create_test_complaint(db, current_status=status)
            # Add history records for non-submitted statuses
            if status != ComplaintStatus.submitted:
                _STATUS_ORDER = ["submitted", "reviewed", "assigned", "resolved"]
                target_idx = _STATUS_ORDER.index(status.value)
                for i in range(1, target_idx + 1):
                    h = ComplaintStatusHistory(
                        complaint_id=c.id,
                        status=ComplaintStatus(_STATUS_ORDER[i]),
                    )
                    db.add(h)
                db.commit()
            created.append(c)

        # Create extra complaints with different issue types
        for it in [IssueType.low_pressure, IssueType.discolored_water]:
            c = _create_test_complaint(db, issue_type=it)
            created.append(c)

        yield created
    finally:
        # Cleanup: remove test complaints and their history
        for c in created:
            db.query(ComplaintStatusHistory).filter(
                ComplaintStatusHistory.complaint_id == c.id
            ).delete()
            db.delete(c)
        db.commit()
        db.close()


# ---- Tests: List all complaints ----


def test_list_all_complaints(test_complaints, auth_headers):
    """Verify GET /api/v1/admin/complaints returns paginated results."""
    response = client.get("/api/v1/admin/complaints", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= len(test_complaints)
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_newest_first_ordering(test_complaints, auth_headers):
    """Verify complaints are returned newest-first by default."""
    response = client.get("/api/v1/admin/complaints?page_size=100", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    if len(items) >= 2:
        for i in range(len(items) - 1):
            assert items[i]["created_at"] >= items[i + 1]["created_at"]


# ---- Tests: Pagination ----


def test_pagination(test_complaints, auth_headers):
    """Verify pagination returns correct page metadata."""
    response = client.get("/api/v1/admin/complaints?page=1&page_size=2", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] >= 1


def test_pagination_page_2(test_complaints, auth_headers):
    """Verify page 2 returns different items than page 1."""
    r1 = client.get("/api/v1/admin/complaints?page=1&page_size=2", headers=auth_headers)
    r2 = client.get("/api/v1/admin/complaints?page=2&page_size=2", headers=auth_headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    items1 = {i["reference_id"] for i in r1.json()["items"]}
    items2 = {i["reference_id"] for i in r2.json()["items"]}
    # Pages should not overlap
    assert items1.isdisjoint(items2)


# ---- Tests: Filter by status ----


def test_filter_by_submitted(test_complaints, auth_headers):
    """Verify filtering by submitted status."""
    response = client.get("/api/v1/admin/complaints?current_status=submitted", headers=auth_headers)
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["current_status"] == "submitted"


def test_filter_by_reviewed(test_complaints, auth_headers):
    """Verify filtering by reviewed status."""
    response = client.get("/api/v1/admin/complaints?current_status=reviewed", headers=auth_headers)
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["current_status"] == "reviewed"


def test_filter_by_assigned(test_complaints, auth_headers):
    """Verify filtering by assigned status."""
    response = client.get("/api/v1/admin/complaints?current_status=assigned", headers=auth_headers)
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["current_status"] == "assigned"


def test_filter_by_resolved(test_complaints, auth_headers):
    """Verify filtering by resolved status."""
    response = client.get("/api/v1/admin/complaints?current_status=resolved", headers=auth_headers)
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["current_status"] == "resolved"


# ---- Tests: Filter by issue type ----


def test_filter_by_issue_type(test_complaints, auth_headers):
    """Verify filtering by issue type."""
    response = client.get("/api/v1/admin/complaints?issue_type=water_leakage", headers=auth_headers)
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["issue_type"] == "water_leakage"


# ---- Tests: Combined filters ----


def test_combined_filters(test_complaints, auth_headers):
    """Verify combined status + issue type filtering."""
    response = client.get(
        "/api/v1/admin/complaints?current_status=submitted&issue_type=water_leakage",
        headers=auth_headers,
    )
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["current_status"] == "submitted"
        assert item["issue_type"] == "water_leakage"


# ---- Tests: Detail ----


def test_get_complaint_detail(test_complaints, auth_headers):
    """Verify GET /{reference_id} returns complete complaint information."""
    ref = test_complaints[0].reference_id
    response = client.get(f"/api/v1/admin/complaints/{ref}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["reference_id"] == ref
    assert "issue_type" in data
    assert "description" in data
    assert "latitude" in data
    assert "longitude" in data
    assert "address" in data
    assert "current_status" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "timeline" in data
    assert isinstance(data["timeline"], list)
    assert len(data["timeline"]) == 4  # submitted, reviewed, assigned, resolved


def test_unknown_complaint_returns_404(auth_headers):
    """Verify unknown reference ID returns 404."""
    response = client.get("/api/v1/admin/complaints/AQS-9999-9999", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---- Tests: Status transitions ----


def test_submitted_to_reviewed(auth_headers):
    """Verify submitted → reviewed transition succeeds."""
    db = SessionLocal()
    try:
        c = _create_test_complaint(db)
        ref = c.reference_id

        response = client.patch(
            f"/api/v1/admin/complaints/{ref}/status",
            json={"status": "reviewed"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["previous_status"] == "submitted"
        assert data["current_status"] == "reviewed"

        # Cleanup
        db.query(ComplaintStatusHistory).filter(
            ComplaintStatusHistory.complaint_id == c.id
        ).delete()
        db.delete(c)
        db.commit()
    finally:
        db.close()


def test_reviewed_to_assigned(auth_headers):
    """Verify reviewed → assigned transition succeeds."""
    db = SessionLocal()
    try:
        c = _create_test_complaint(db, current_status=ComplaintStatus.reviewed)
        ref = c.reference_id

        response = client.patch(
            f"/api/v1/admin/complaints/{ref}/status",
            json={"status": "assigned"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["previous_status"] == "reviewed"
        assert data["current_status"] == "assigned"

        # Cleanup
        db.query(ComplaintStatusHistory).filter(
            ComplaintStatusHistory.complaint_id == c.id
        ).delete()
        db.delete(c)
        db.commit()
    finally:
        db.close()


def test_assigned_to_resolved(auth_headers):
    """Verify assigned → resolved transition succeeds."""
    db = SessionLocal()
    try:
        c = _create_test_complaint(db, current_status=ComplaintStatus.assigned)
        ref = c.reference_id

        response = client.patch(
            f"/api/v1/admin/complaints/{ref}/status",
            json={"status": "resolved"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["previous_status"] == "assigned"
        assert data["current_status"] == "resolved"

        # Cleanup
        db.query(ComplaintStatusHistory).filter(
            ComplaintStatusHistory.complaint_id == c.id
        ).delete()
        db.delete(c)
        db.commit()
    finally:
        db.close()


def test_backward_transition_rejected(auth_headers):
    """Verify backward status transition is rejected with 409."""
    db = SessionLocal()
    try:
        c = _create_test_complaint(db, current_status=ComplaintStatus.reviewed)
        ref = c.reference_id

        response = client.patch(
            f"/api/v1/admin/complaints/{ref}/status",
            json={"status": "submitted"},
            headers=auth_headers,
        )
        assert response.status_code == 409
        assert "backward" in response.json()["detail"].lower() or "cannot" in response.json()["detail"].lower()

        # Cleanup
        db.query(ComplaintStatusHistory).filter(
            ComplaintStatusHistory.complaint_id == c.id
        ).delete()
        db.delete(c)
        db.commit()
    finally:
        db.close()


def test_skip_status_rejected(auth_headers):
    """Verify skipping status stages is rejected with 409."""
    db = SessionLocal()
    try:
        c = _create_test_complaint(db)
        ref = c.reference_id

        response = client.patch(
            f"/api/v1/admin/complaints/{ref}/status",
            json={"status": "resolved"},
            headers=auth_headers,
        )
        assert response.status_code == 409
        assert "skip" in response.json()["detail"].lower() or "next allowed" in response.json()["detail"].lower()

        # Cleanup
        db.query(ComplaintStatusHistory).filter(
            ComplaintStatusHistory.complaint_id == c.id
        ).delete()
        db.delete(c)
        db.commit()
    finally:
        db.close()


def test_invalid_status_rejected(auth_headers):
    """Verify invalid status value returns 422."""
    db = SessionLocal()
    try:
        c = _create_test_complaint(db)
        ref = c.reference_id

        response = client.patch(
            f"/api/v1/admin/complaints/{ref}/status",
            json={"status": "invalid_status"},
            headers=auth_headers,
        )
        assert response.status_code == 422

        # Cleanup
        db.query(ComplaintStatusHistory).filter(
            ComplaintStatusHistory.complaint_id == c.id
        ).delete()
        db.delete(c)
        db.commit()
    finally:
        db.close()


# ---- Tests: Summary stats ----


def test_summary_stats(test_complaints, auth_headers):
    """Verify summary statistics return correct dynamic counts."""
    response = client.get("/api/v1/admin/complaints/stats/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_complaints" in data
    assert "submitted" in data
    assert "reviewed" in data
    assert "assigned" in data
    assert "resolved" in data
    assert "open_complaints" in data
    assert data["total_complaints"] >= len(test_complaints)
    assert data["open_complaints"] == data["total_complaints"] - data["resolved"]
    # All status counts should sum to total
    assert (data["submitted"] + data["reviewed"] + data["assigned"] + data["resolved"]
            == data["total_complaints"])


# ---- Tests: Status history ----


def test_status_history_created_on_transition(auth_headers):
    """Verify status transitions create history events."""
    db = SessionLocal()
    try:
        c = _create_test_complaint(db)
        ref = c.reference_id

        # Transition to reviewed
        response = client.patch(
            f"/api/v1/admin/complaints/{ref}/status",
            json={"status": "reviewed"},
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Check history was created
        history = (
            db.query(ComplaintStatusHistory)
            .filter(ComplaintStatusHistory.complaint_id == c.id)
            .order_by(ComplaintStatusHistory.created_at.asc())
            .all()
        )
        assert len(history) >= 2  # submitted + reviewed
        status_values = [h.status.value if hasattr(h.status, 'value') else str(h.status) for h in history]
        assert "submitted" in status_values
        assert "reviewed" in status_values

        # Cleanup
        db.query(ComplaintStatusHistory).filter(
            ComplaintStatusHistory.complaint_id == c.id
        ).delete()
        db.delete(c)
        db.commit()
    finally:
        db.close()


def test_citizen_tracking_returns_correct_timeline(auth_headers):
    """Verify citizen tracking API returns real timeline after status transition."""
    db = SessionLocal()
    try:
        c = _create_test_complaint(db)
        ref = c.reference_id

        # Transition to reviewed
        client.patch(
            f"/api/v1/admin/complaints/{ref}/status",
            json={"status": "reviewed"},
            headers=auth_headers,
        )

        # Check citizen tracking endpoint
        response = client.get(f"/api/v1/complaints/{ref}")
        assert response.status_code == 200
        data = response.json()
        timeline = data["timeline"]

        # submitted should have a timestamp
        submitted_event = next(e for e in timeline if e["status"] == "submitted")
        assert submitted_event["timestamp"] is not None

        # reviewed should have a timestamp (from real history)
        reviewed_event = next(e for e in timeline if e["status"] == "reviewed")
        assert reviewed_event["timestamp"] is not None

        # assigned and resolved should NOT have timestamps
        assigned_event = next(e for e in timeline if e["status"] == "assigned")
        assert assigned_event["timestamp"] is None
        resolved_event = next(e for e in timeline if e["status"] == "resolved")
        assert resolved_event["timestamp"] is None

        # Cleanup
        db.query(ComplaintStatusHistory).filter(
            ComplaintStatusHistory.complaint_id == c.id
        ).delete()
        db.delete(c)
        db.commit()
    finally:
        db.close()


# ---- Tests: Same-status no-op ----


def test_same_status_no_op(auth_headers):
    """Verify requesting the same status is handled gracefully."""
    db = SessionLocal()
    try:
        c = _create_test_complaint(db)
        ref = c.reference_id

        response = client.patch(
            f"/api/v1/admin/complaints/{ref}/status",
            json={"status": "submitted"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["previous_status"] == "submitted"
        assert data["current_status"] == "submitted"

        # Cleanup
        db.query(ComplaintStatusHistory).filter(
            ComplaintStatusHistory.complaint_id == c.id
        ).delete()
        db.delete(c)
        db.commit()
    finally:
        db.close()
