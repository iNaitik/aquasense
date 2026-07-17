"""Tests for rolling 30-day complaint feature calculations (`recalculate_pipeline_risk_from_complaints`).

Covers (Section 17):
- Matched complaint increases effective total complaint count.
- water_leakage increases both total and leakage counts.
- low_pressure increases total but not leakage count.
- discolored_water increases total but not leakage count.
- Complaints older than 30 days do not contribute to dynamic rolling counts.
- Baseline counts are preserved.
- Multiple complaints on the same pipeline are counted correctly.
"""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.pipeline import Pipeline
from app.models.complaint import Complaint, ComplaintStatus, IssueType
from app.models.complaint_status_history import ComplaintStatusHistory
from app.services.pipeline_recalculation_service import recalculate_pipeline_risk_from_complaints


@pytest.fixture(scope="function")
def test_pipeline():
    """Create a temporary test pipeline segment for isolated feature testing."""
    db: Session = SessionLocal()
    pipe = Pipeline(
        pipeline_id="TEST-FEAT-PIPE",
        start_latitude=22.7100,
        start_longitude=75.8200,
        end_latitude=22.7110,
        end_longitude=75.8210,
        center_latitude=22.7105,
        center_longitude=75.8205,
        pipe_age_years=25.0,
        material="CI",
        diameter_mm=300.0,
        length_m=150.0,
        previous_failures=1,
        days_since_last_maintenance=200.0,
        baseline_complaints_30d=2,
        baseline_leakage_complaints_30d=1,
        complaints_last_30_days=2,
        leakage_complaints_30d=1,
        failure_probability=0.2,
        risk_score=20.0,
        risk_level="LOW",
    )
    db.add(pipe)
    db.commit()
    db.refresh(pipe)
    try:
        yield pipe
    finally:
        db.query(Complaint).filter(Complaint.matched_pipeline_id == pipe.id).delete()
        db.query(Pipeline).filter(Pipeline.id == pipe.id).delete()
        db.commit()
        db.close()


import uuid

def _add_complaint(db: Session, pipeline_id: int, issue_type: IssueType, created_at: datetime | None = None) -> Complaint:
    """Helper to insert a complaint directly linked to a test pipeline."""
    c = Complaint(
        reference_id=f"AQUA-TF-{uuid.uuid4().hex[:8].upper()}",
        issue_type=issue_type,
        description="Test complaint for rolling 30-day feature verification",
        latitude=22.7105,
        longitude=75.8205,
        address="Test Pipe Address",
        current_status=ComplaintStatus.submitted,
        matched_pipeline_id=pipeline_id,
        pipeline_distance_m=5.0,
    )
    if created_at:
        c.created_at = created_at
    db.add(c)
    db.flush()
    history = ComplaintStatusHistory(complaint_id=c.id, status=ComplaintStatus.submitted)
    if created_at:
        history.created_at = created_at
    db.add(history)
    db.commit()
    db.refresh(c)
    return c


def test_baseline_counts_preserved_and_initial_state(test_pipeline):
    """Verify initial state and that baseline counts are preserved accurately."""
    db: Session = SessionLocal()
    try:
        pipe = db.query(Pipeline).filter_by(id=test_pipeline.id).first()
        recalculate_pipeline_risk_from_complaints(db, pipe)
        assert pipe.baseline_complaints_30d == 2
        assert pipe.baseline_leakage_complaints_30d == 1
        assert pipe.complaints_last_30_days == 2
        assert pipe.leakage_complaints_30d == 1
    finally:
        db.close()


def test_water_leakage_increases_both_total_and_leakage_counts(test_pipeline):
    """Verify water_leakage increases both total complaint count and leakage count."""
    db: Session = SessionLocal()
    try:
        _add_complaint(db, test_pipeline.id, IssueType.water_leakage)
        pipe = db.query(Pipeline).filter_by(id=test_pipeline.id).first()
        recalculate_pipeline_risk_from_complaints(db, pipe)

        # Baseline (2 total, 1 leakage) + 1 real water_leakage -> (3 total, 2 leakage)
        assert pipe.complaints_last_30_days == 3
        assert pipe.leakage_complaints_30d == 2
        assert pipe.baseline_complaints_30d == 2
        assert pipe.baseline_leakage_complaints_30d == 1
    finally:
        db.close()


def test_low_pressure_increases_total_but_not_leakage_count(test_pipeline):
    """Verify low_pressure increases total complaint count but not leakage count."""
    db: Session = SessionLocal()
    try:
        _add_complaint(db, test_pipeline.id, IssueType.low_pressure)
        pipe = db.query(Pipeline).filter_by(id=test_pipeline.id).first()
        recalculate_pipeline_risk_from_complaints(db, pipe)

        # Baseline (2 total, 1 leakage) + 1 real low_pressure -> (3 total, 1 leakage)
        assert pipe.complaints_last_30_days == 3
        assert pipe.leakage_complaints_30d == 1
    finally:
        db.close()


def test_discolored_water_increases_total_but_not_leakage_count(test_pipeline):
    """Verify discolored_water increases total complaint count but not leakage count."""
    db: Session = SessionLocal()
    try:
        _add_complaint(db, test_pipeline.id, IssueType.discolored_water)
        pipe = db.query(Pipeline).filter_by(id=test_pipeline.id).first()
        recalculate_pipeline_risk_from_complaints(db, pipe)

        # Baseline (2 total, 1 leakage) + 1 real discolored_water -> (3 total, 1 leakage)
        assert pipe.complaints_last_30_days == 3
        assert pipe.leakage_complaints_30d == 1
    finally:
        db.close()


def test_complaints_older_than_30_days_do_not_contribute(test_pipeline):
    """Verify complaints older than 30 days are excluded from rolling counts."""
    db: Session = SessionLocal()
    try:
        old_time = datetime.now(timezone.utc) - timedelta(days=32)
        _add_complaint(db, test_pipeline.id, IssueType.water_leakage, created_at=old_time)

        pipe = db.query(Pipeline).filter_by(id=test_pipeline.id).first()
        recalculate_pipeline_risk_from_complaints(db, pipe)

        # Since the complaint is 32 days old, only baseline remains (2 total, 1 leakage)
        assert pipe.complaints_last_30_days == 2
        assert pipe.leakage_complaints_30d == 1
    finally:
        db.close()


def test_multiple_complaints_counted_correctly(test_pipeline):
    """Verify multiple complaints of various types on the same pipeline are aggregated correctly."""
    db: Session = SessionLocal()
    try:
        # Add 2 water_leakage within 30 days
        _add_complaint(db, test_pipeline.id, IssueType.water_leakage)
        _add_complaint(db, test_pipeline.id, IssueType.water_leakage)
        # Add 1 unusual_flow within 30 days
        _add_complaint(db, test_pipeline.id, IssueType.unusual_flow)
        # Add 1 water_leakage older than 30 days (should be ignored)
        old_time = datetime.now(timezone.utc) - timedelta(days=40)
        _add_complaint(db, test_pipeline.id, IssueType.water_leakage, created_at=old_time)

        pipe = db.query(Pipeline).filter_by(id=test_pipeline.id).first()
        recalculate_pipeline_risk_from_complaints(db, pipe)

        # Baseline: 2 total, 1 leakage
        # Real valid: +3 total (+2 leakage, +1 unusual_flow)
        # Result: 5 total, 3 leakage
        assert pipe.complaints_last_30_days == 5
        assert pipe.leakage_complaints_30d == 3
    finally:
        db.close()
