"""Tests for geographic pipeline matching service (`find_nearest_pipeline` & endpoints).

Covers (Section 16):
- Complaint close to a pipeline is matched.
- Complaint outside maximum radius is not matched.
- Nearest line segment is selected rather than nearest center point.
- Distance is returned in meters.
- Complaint without coordinates is still created successfully and remains unmatched.
- Invalid coordinates are handled according to existing validation.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models.pipeline import Pipeline
from app.models.complaint import Complaint
from app.models.complaint_status_history import ComplaintStatusHistory
from app.services.pipeline_matching_service import find_nearest_pipeline, _calculate_segment_distance_m

client = TestClient(app)


def test_calculate_segment_distance_in_meters():
    """Verify segment distance calculation returns distance in meters."""
    # Point right on the equator going East 1 degree is ~111,320 meters
    dist = _calculate_segment_distance_m(0.0, 0.0, 0.0, 1.0, 0.0, 2.0)
    # Distance from (0,0) to segment (0,1)-(0,2) should be ~111,320 meters
    assert 111000.0 <= dist <= 112000.0


def test_nearest_line_segment_selected_over_nearest_center_point():
    """Verify nearest line segment is selected rather than nearest center point."""
    db: Session = SessionLocal()
    try:
        # Create two temporary candidate pipelines in DB
        p1 = Pipeline(
            pipeline_id="TEST-SEG-1",
            start_latitude=22.6980,
            start_longitude=75.8000,
            end_latitude=22.7020,
            end_longitude=75.8000,
            center_latitude=22.7000,
            center_longitude=75.8000,
            pipe_age_years=10.0,
            material="DI",
            diameter_mm=200.0,
            length_m=440.0,
            previous_failures=0,
            days_since_last_maintenance=100.0,
            baseline_complaints_30d=0,
            baseline_leakage_complaints_30d=0,
            complaints_last_30_days=0,
            leakage_complaints_30d=0,
            failure_probability=0.1,
            risk_score=10.0,
            risk_level="LOW",
        )
        p2 = Pipeline(
            pipeline_id="TEST-SEG-2",
            start_latitude=22.7018,
            start_longitude=75.8008,
            end_latitude=22.7018,
            end_longitude=75.8009,
            center_latitude=22.7018,
            center_longitude=75.80085,
            pipe_age_years=10.0,
            material="DI",
            diameter_mm=200.0,
            length_m=10.0,
            previous_failures=0,
            days_since_last_maintenance=100.0,
            baseline_complaints_30d=0,
            baseline_leakage_complaints_30d=0,
            complaints_last_30_days=0,
            leakage_complaints_30d=0,
            failure_probability=0.1,
            risk_score=10.0,
            risk_level="LOW",
        )
        db.add_all([p1, p2])
        db.commit()

        # Query point P is at (22.7018, 75.8000)
        # Distance to p1 line segment = 0 meters (since P lies on line x=75.8000 between y=22.6980 and y=22.7020)
        # Distance to p1 center point (22.7000, 75.8000) ~ 199 meters
        # Distance to p2 center/segment (22.7018, 75.8008) ~ 82 meters
        # Center matching would pick p2 (82m < 199m). Segment matching picks p1 (0m < 82m).
        match_result = find_nearest_pipeline(db, 22.7018, 75.8000, max_distance_m=500.0)
        assert match_result is not None
        matched_pipe, dist_m = match_result
        assert matched_pipe.pipeline_id == "TEST-SEG-1"
        assert dist_m < 5.0  # Should be ~0 meters right on the segment

    finally:
        db.query(Pipeline).filter(Pipeline.pipeline_id.in_(["TEST-SEG-1", "TEST-SEG-2"])).delete()
        db.commit()
        db.close()


def test_complaint_close_to_pipeline_is_matched():
    """Verify complaint close to a simulated pipeline is linked on submission."""
    # Submit complaint at IND-PIPE-00001 start point (22.724517, 75.843688)
    response = client.post(
        "/api/v1/complaints",
        data={
            "citizen_name": "Test Citizen",
            "phone_number": "+919876543210",
            "issue_type": "water_leakage",
            "description": "Water leaking rapidly near start of pipeline IND-PIPE-00001",
            "latitude": "22.724517",
            "longitude": "75.843688",
            "address": "Close to IND-PIPE-00001, Indore",
        },
    )
    assert response.status_code == 201
    ref_id = response.json()["reference_id"]

    db: Session = SessionLocal()
    try:
        complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
        assert complaint is not None
        assert complaint.matched_pipeline_id is not None
        assert complaint.pipeline_distance_m is not None
        assert complaint.pipeline_distance_m < 10.0
        assert complaint.matched_pipeline.pipeline_id == "IND-PIPE-00001"
    finally:
        if complaint:
            db.delete(complaint)
            db.commit()
        db.close()


def test_complaint_outside_max_radius_is_not_matched():
    """Verify complaint outside configured maximum matching radius remains unmatched."""
    # Coordinates (10.0, 10.0) are far outside Indore
    response = client.post(
        "/api/v1/complaints",
        data={
            "citizen_name": "Test Citizen",
            "phone_number": "+919876543210",
            "issue_type": "low_pressure",
            "description": "Complaint with coordinates far outside matching range",
            "latitude": "10.000000",
            "longitude": "10.000000",
            "address": "Far Away Location",
        },
    )
    assert response.status_code == 201
    ref_id = response.json()["reference_id"]

    db: Session = SessionLocal()
    try:
        complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
        assert complaint is not None
        assert complaint.matched_pipeline_id is None
        assert complaint.pipeline_distance_m is None
    finally:
        if complaint:
            db.delete(complaint)
            db.commit()
        db.close()


def test_complaint_without_coordinates_succeeds_and_unmatched():
    """Verify complaint submitted with only address (no coords) succeeds and is unmatched."""
    response = client.post(
        "/api/v1/complaints",
        data={
            "citizen_name": "Test Citizen",
            "phone_number": "+919876543210",
            "issue_type": "discolored_water",
            "description": "Dirty brown water flowing from tap without coordinates",
            "address": "MG Road, Indore (Address Only)",
        },
    )
    assert response.status_code == 201
    ref_id = response.json()["reference_id"]

    db: Session = SessionLocal()
    try:
        complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
        assert complaint is not None
        assert complaint.latitude is None
        assert complaint.longitude is None
        assert complaint.matched_pipeline_id is None
    finally:
        if complaint:
            db.delete(complaint)
            db.commit()
        db.close()


def test_invalid_coordinates_handled_by_existing_validation():
    """Verify out-of-range coordinates are rejected with 422 Unprocessable Entity."""
    response = client.post(
        "/api/v1/complaints",
        data={
            "issue_type": "water_leakage",
            "description": "Trying to submit with latitude > 90",
            "latitude": "150.0",
            "longitude": "75.0",
        },
    )
    assert response.status_code == 422
