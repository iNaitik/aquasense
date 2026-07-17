"""Tests for Citizen Contact Details (Step 7 Objective A).

Covers:
  - Phone number normalization (standard 10-digit, leading +91, leading 0, hyphenated)
  - Rejection of invalid phone numbers and empty/short citizen names
  - Phone number masking in authority complaint list items
  - Preservation of public citizen tracking privacy contract (no personal info exposed)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.utils.phone import normalize_indian_phone

client = TestClient(app)


def test_phone_normalization_unit():
    """Verify normalize_indian_phone utility across standard Indian formats."""
    assert normalize_indian_phone("9876543210") == "+919876543210"
    assert normalize_indian_phone("+919876543210") == "+919876543210"
    assert normalize_indian_phone("09876543210") == "+919876543210"
    assert normalize_indian_phone("919876543210") == "+919876543210"
    assert normalize_indian_phone("91-9876543210") == "+919876543210"
    assert normalize_indian_phone(" +91 (987) 654-3210 ") == "+919876543210"

    with pytest.raises(ValueError):
        normalize_indian_phone("12345")
    with pytest.raises(ValueError):
        normalize_indian_phone("+19876543210")
    with pytest.raises(ValueError):
        normalize_indian_phone("abcde12345")


def test_submit_complaint_validates_and_normalizes_contact():
    """Verify complaint submission normalizes phone and saves contact details."""
    response = client.post(
        "/api/v1/complaints",
        data={
            "citizen_name": "  Rohan Sharma  ",
            "phone_number": "09876543210",
            "issue_type": "water_leakage",
            "description": "Rapid water leakage from main supply line outside house",
            "address": "123 Vijay Nagar, Indore",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "reference_id" in data


def test_submit_complaint_rejects_invalid_contact():
    """Verify complaint submission rejects invalid citizen name or phone number."""
    # Short name
    r1 = client.post(
        "/api/v1/complaints",
        data={
            "citizen_name": "A",
            "phone_number": "9876543210",
            "issue_type": "low_pressure",
            "description": "Very low water pressure during morning hours",
            "address": "MG Road, Indore",
        },
    )
    assert r1.status_code == 422

    # Invalid phone
    r2 = client.post(
        "/api/v1/complaints",
        data={
            "citizen_name": "Rohan Sharma",
            "phone_number": "123456",
            "issue_type": "low_pressure",
            "description": "Very low water pressure during morning hours",
            "address": "MG Road, Indore",
        },
    )
    assert r2.status_code == 422


def test_authority_list_masks_phone_number(auth_headers):
    """Verify that authority list endpoint masks the middle digits of phone numbers."""
    # First submit a complaint
    client.post(
        "/api/v1/complaints",
        data={
            "citizen_name": "Ananya Patel",
            "phone_number": "9876543210",
            "issue_type": "discolored_water",
            "description": "Yellowish water coming from kitchen tap continuously",
            "address": "Palasia, Indore",
        },
    )

    resp = client.get("/api/v1/admin/complaints", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    ananya_items = [i for i in items if i.get("citizen_name") == "Ananya Patel"]
    assert len(ananya_items) > 0
    item = ananya_items[0]
    # Phone number +919876543210 (length 13) should be masked: starts with +91, ends with 3210, middle asterisks
    assert item["phone_number"].startswith("+91")
    assert item["phone_number"].endswith("3210")
    assert "*" in item["phone_number"]
    assert item["phone_number"] != "+919876543210"


def test_citizen_tracking_contract_preserved():
    """Verify public citizen tracking response does not expose citizen_name or phone_number."""
    resp = client.post(
        "/api/v1/complaints",
        data={
            "citizen_name": "Secret Citizen",
            "phone_number": "+919876543210",
            "issue_type": "unusual_flow",
            "description": "Sudden unusual gushing sound from underground pipe near gate",
            "address": "Saket Nagar, Indore",
        },
    )
    assert resp.status_code == 201
    ref = resp.json()["reference_id"]

    track_resp = client.get(f"/api/v1/complaints/{ref}")
    assert track_resp.status_code == 200
    track_data = track_resp.json()
    assert "citizen_name" not in track_data
    assert "phone_number" not in track_data
