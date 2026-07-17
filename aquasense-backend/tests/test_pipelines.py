"""Tests for AQUA-SENSE Pipeline API endpoints and ML Prediction Service.

DISCLAIMER:
The pipeline network used in this prototype is simulated and does not represent official
Indore Municipal Corporation infrastructure. The ML model was trained on synthetic historical data.
Risk predictions are prototype demonstration outputs and are not validated assessments of real
Indore water pipelines.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.pipeline_prediction_service import predict_pipeline_risk

client = TestClient(app)


def test_get_all_pipelines(auth_headers):
    """Verify GET all pipelines returns lightweight map items with status 200."""
    response = client.get("/api/v1/pipelines", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 750  # All imported simulated segments
    if len(data) > 0:
        item = data[0]
        assert "pipeline_id" in item
        assert "start_latitude" in item
        assert "start_longitude" in item
        assert "end_latitude" in item
        assert "end_longitude" in item
        assert "risk_score" in item
        assert "risk_level" in item
        # Ensure heavy internal DB/ML fields are not exposed in map items
        assert "id" not in item
        assert "created_at" not in item
        assert "complaints_last_30_days" not in item


def test_filter_pipelines_by_low_risk(auth_headers):
    """Verify filtering pipelines by LOW risk level."""
    response = client.get("/api/v1/pipelines?risk_level=LOW", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 385
    for item in data:
        assert item["risk_level"] == "LOW"


def test_filter_pipelines_by_medium_risk(auth_headers):
    """Verify filtering pipelines by MEDIUM risk level."""
    response = client.get("/api/v1/pipelines?risk_level=MEDIUM", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 181
    for item in data:
        assert item["risk_level"] == "MEDIUM"


def test_filter_pipelines_by_high_risk(auth_headers):
    """Verify filtering pipelines by HIGH risk level."""
    response = client.get("/api/v1/pipelines?risk_level=HIGH", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 184
    for item in data:
        assert item["risk_level"] == "HIGH"


def test_get_pipeline_by_id_success(auth_headers):
    """Verify retrieving detailed information for a specific existing pipeline segment."""
    response = client.get("/api/v1/pipelines/IND-PIPE-00001", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["pipeline_id"] == "IND-PIPE-00001"
    assert "pipe_age_years" in data
    assert "material" in data
    assert "diameter_mm" in data
    assert "length_m" in data
    assert "previous_failures" in data
    assert "days_since_last_maintenance" in data
    assert "complaints_last_30_days" in data
    assert "leakage_complaints_30d" in data
    assert "failure_probability" in data
    assert "risk_score" in data
    assert "risk_level" in data


def test_get_unknown_pipeline_returns_404(auth_headers):
    """Verify retrieving an unknown pipeline returns HTTP 404."""
    response = client.get("/api/v1/pipelines/IND-PIPE-9999-UNKNOWN", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_pipeline_summary_statistics(auth_headers):
    """Verify summary statistics endpoint returns total count, risk distribution, and avg score."""
    response = client.get("/api/v1/pipelines/stats/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_pipelines"] == 750
    assert data["risk_distribution"]["LOW"] == 385
    assert data["risk_distribution"]["MEDIUM"] == 181
    assert data["risk_distribution"]["HIGH"] == 184
    assert isinstance(data["average_risk_score"], float)
    assert 0.0 <= data["average_risk_score"] <= 100.0
    assert abs(data["average_risk_score"] - 44.34) < 0.1


def test_ml_prediction_service_valid_input_and_bounds():
    """Verify ML prediction service accepts valid inputs and returns probability/score/level within strict bounds."""
    sample_features = {
        "pipe_age_years": 50.0,
        "material": "DI",
        "diameter_mm": 200.0,
        "length_m": 150.0,
        "previous_failures": 2,
        "days_since_last_maintenance": 400.0,
        "complaints_last_30_days": 3,
        "leakage_complaints_30d": 2,
    }
    result = predict_pipeline_risk(sample_features)
    assert "failure_probability" in result
    assert "risk_score" in result
    assert "risk_level" in result

    prob = result["failure_probability"]
    score = result["risk_score"]
    level = result["risk_level"]

    # Verify bounds
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0

    assert isinstance(score, float)
    assert 0.0 <= score <= 100.0
    assert round(prob * 100.0, 1) == score

    assert level in {"LOW", "MEDIUM", "HIGH"}
    if score < 40.0:
        assert level == "LOW"
    elif score < 70.0:
        assert level == "MEDIUM"
    else:
        assert level == "HIGH"


def test_ml_prediction_service_missing_feature_raises():
    """Verify ML prediction service raises ValueError when required feature is missing."""
    incomplete_features = {
        "pipe_age_years": 30.0,
        "material": "PVC",
    }
    with pytest.raises(ValueError, match="Missing required ML input feature"):
        predict_pipeline_risk(incomplete_features)
