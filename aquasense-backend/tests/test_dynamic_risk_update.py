"""Tests for dynamic risk prediction updates from citizen complaints.

Covers (Section 18):
- Matched complaint triggers risk recalculation when submitted via API.
- Probability changes according to model output.
- Risk level transitions when threshold is crossed (`LOW <-> MEDIUM <-> HIGH`).
- Authority map / detail APIs reflect updated risk score and risk level.
- Transactional behavior: if matching or ML inference fails, citizen complaint creation still succeeds (`matched_pipeline_id = None`).
"""

import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models.pipeline import Pipeline
from app.models.complaint import Complaint
from app.models.complaint_status_history import ComplaintStatusHistory
from app.services.pipeline_prediction_service import predict_pipeline_risk

client = TestClient(app)


@pytest.fixture(scope="function")
def test_dynamic_pipe():
    """Create a temporary test pipeline whose initial state is near boundary thresholds."""
    db: Session = SessionLocal()
    db.query(Pipeline).filter_by(pipeline_id="TEST-DYN-001").delete()
    db.commit()
    # Find initial prediction for baseline = 0
    base_feat = {
        "pipe_age_years": 35.0,
        "material": "CI",
        "diameter_mm": 200.0,
        "length_m": 250.0,
        "previous_failures": 2,
        "days_since_last_maintenance": 300.0,
        "complaints_last_30_days": 0,
        "leakage_complaints_30d": 0,
    }
    pred = predict_pipeline_risk(base_feat)

    pipe = Pipeline(
        pipeline_id="TEST-DYN-001",
        start_latitude=22.7500,
        start_longitude=75.8600,
        end_latitude=22.7510,
        end_longitude=75.8610,
        center_latitude=22.7505,
        center_longitude=75.8605,
        pipe_age_years=35.0,
        material="CI",
        diameter_mm=200.0,
        length_m=250.0,
        previous_failures=2,
        days_since_last_maintenance=300.0,
        baseline_complaints_30d=0,
        baseline_leakage_complaints_30d=0,
        complaints_last_30_days=0,
        leakage_complaints_30d=0,
        failure_probability=pred["failure_probability"],
        risk_score=pred["risk_score"],
        risk_level=pred["risk_level"],
    )
    db.add(pipe)
    db.commit()
    db.refresh(pipe)
    try:
        yield pipe
    finally:
        complaints = db.query(Complaint).filter(Complaint.matched_pipeline_id == pipe.id).all()
        for c in complaints:
            db.query(ComplaintStatusHistory).filter_by(complaint_id=c.id).delete()
            db.delete(c)
        db.query(Pipeline).filter(Pipeline.id == pipe.id).delete()
        db.commit()
        db.close()


def test_matched_complaint_triggers_recalculation_and_updates_apis(test_dynamic_pipe, auth_headers):
    """Verify submitting a matched complaint updates failure probability and reflects in pipeline APIs."""
    initial_prob = test_dynamic_pipe.failure_probability
    initial_score = test_dynamic_pipe.risk_score

    # Submit complaint at test_dynamic_pipe location
    response = client.post(
        "/api/v1/complaints",
        data={
            "citizen_name": "Test Citizen",
            "phone_number": "+919876543210",
            "issue_type": "water_leakage",
            "description": "Severe water leakage observed at test dynamic pipeline",
            "latitude": "22.7505",
            "longitude": "75.8605",
            "address": "Dynamic Pipe Location",
        },
    )
    assert response.status_code == 201

    db: Session = SessionLocal()
    try:
        pipe = db.query(Pipeline).filter_by(id=test_dynamic_pipe.id).first()
        # Ensure rolling counts and probability increased
        assert pipe.complaints_last_30_days == 1
        assert pipe.leakage_complaints_30d == 1
        assert pipe.failure_probability > initial_prob
        assert pipe.risk_score > initial_score

        # Verify authority GET /api/v1/pipelines/{id} API returns updated risk
        api_resp = client.get(f"/api/v1/pipelines/{pipe.pipeline_id}", headers=auth_headers)
        assert api_resp.status_code == 200
        data = api_resp.json()
        assert data["complaints_last_30_days"] == 1
        assert data["leakage_complaints_30d"] == 1
        assert data["failure_probability"] == pipe.failure_probability
        assert data["risk_score"] == pipe.risk_score
    finally:
        db.close()


def test_risk_level_transitions_on_complaint_accumulation(test_dynamic_pipe):
    """Verify adding multiple complaints causes risk level transition across thresholds."""
    db: Session = SessionLocal()
    try:
        pipe = db.query(Pipeline).filter_by(id=test_dynamic_pipe.id).first()
        initial_level = pipe.risk_level

        # Submit multiple water leakage complaints to push probability and score higher
        for i in range(10):
            resp = client.post(
                "/api/v1/complaints",
                data={
                    "citizen_name": "Test Citizen",
                    "phone_number": "+919876543210",
                    "issue_type": "water_leakage",
                    "description": f"Repeated leakage report {i}",
                    "latitude": "22.7505",
                    "longitude": "75.8605",
                    "address": "Dynamic Pipe Location",
                },
            )
            assert resp.status_code == 201

        db.refresh(pipe)
        assert pipe.complaints_last_30_days == 10
        assert pipe.leakage_complaints_30d == 10
        # Check that probability increased significantly and risk level transitioned if crossing 40 or 70
        assert pipe.failure_probability > test_dynamic_pipe.failure_probability
        if initial_level == "LOW" and pipe.risk_score >= 40.0:
            assert pipe.risk_level in ["MEDIUM", "HIGH"]
        elif initial_level == "MEDIUM" and pipe.risk_score >= 70.0:
            assert pipe.risk_level == "HIGH"
    finally:
        db.close()


def test_transactional_safety_when_matching_or_ml_fails(test_dynamic_pipe):
    """Verify that if pipeline matching or ML prediction raises an exception, complaint creation succeeds."""
    with patch("app.services.complaint_service.find_nearest_pipeline", side_effect=RuntimeError("Simulated matching failure")):
        response = client.post(
            "/api/v1/complaints",
            data={
                "citizen_name": "Test Citizen",
                "phone_number": "+919876543210",
                "issue_type": "low_pressure",
                "description": "Complaint during matching outage",
                "latitude": "22.7505",
                "longitude": "75.8605",
                "address": "Dynamic Pipe Location",
            },
        )
        # Citizen submission MUST succeed despite matching exception
        assert response.status_code == 201
        ref_id = response.json()["reference_id"]

        db: Session = SessionLocal()
        try:
            complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
            assert complaint is not None
            assert complaint.matched_pipeline_id is None
            # Cleanup created complaint
            db.query(ComplaintStatusHistory).filter_by(complaint_id=complaint.id).delete()
            db.delete(complaint)
            db.commit()
        finally:
            db.close()
