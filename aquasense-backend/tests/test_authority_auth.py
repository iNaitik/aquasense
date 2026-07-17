"""Tests for Authority Authentication & Authorization (Step 7 Objective B).

Covers:
  - Secure login with valid email and password returning JWT access token and user profile
  - Rejection of invalid credentials (generic error to prevent account enumeration)
  - Profile endpoint (/api/v1/auth/authority/me) returning correct info when authenticated and 401 when not
  - Enforcement of authentication on all authority complaint and pipeline endpoints (401 Unauthorized)
  - Verification that citizen complaint routes remain public without authentication required
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_authority_login_success(auth_user):
    """Verify login with correct credentials returns valid JWT token and authority profile."""
    response = client.post(
        "/api/v1/auth/authority/login",
        json={"email": auth_user.email, "password": "SecureTestPass1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert "authority" in data
    assert data["authority"]["email"] == auth_user.email
    assert data["authority"]["name"] == auth_user.name
    assert data["authority"]["id"] == auth_user.id


def test_authority_login_wrong_password(auth_user):
    """Verify login fails with HTTP 401 when password is incorrect."""
    response = client.post(
        "/api/v1/auth/authority/login",
        json={"email": auth_user.email, "password": "WrongPassword999"},
    )
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


def test_authority_login_unknown_email():
    """Verify login fails with HTTP 401 and generic error when email does not exist."""
    response = client.post(
        "/api/v1/auth/authority/login",
        json={"email": "nonexistent@aquasense.org", "password": "SomePassword123"},
    )
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


def test_get_current_authority_me(auth_headers, auth_user):
    """Verify /me endpoint returns profile when authenticated with valid Bearer token."""
    response = client.get("/api/v1/auth/authority/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == auth_user.id
    assert data["email"] == auth_user.email
    assert data["name"] == auth_user.name


def test_get_current_authority_me_unauthorized():
    """Verify /me endpoint returns HTTP 401 without valid Bearer token."""
    response = client.get("/api/v1/auth/authority/me")
    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()


def test_protected_routes_require_authentication():
    """Verify authority management and pipeline endpoints reject unauthenticated requests with 401."""
    endpoints = [
        ("/api/v1/admin/complaints", "GET"),
        ("/api/v1/admin/complaints/stats/summary", "GET"),
        ("/api/v1/pipelines", "GET"),
        ("/api/v1/pipelines/stats/summary", "GET"),
    ]
    for url, method in endpoints:
        if method == "GET":
            resp = client.get(url)
            assert resp.status_code == 401, f"Expected 401 for GET {url}, got {resp.status_code}"


def test_citizen_routes_remain_public():
    """Verify citizen complaint submission and status check work without authentication."""
    # Submit public complaint
    submit_resp = client.post(
        "/api/v1/complaints",
        data={
            "citizen_name": "Public Citizen",
            "phone_number": "9876543210",
            "issue_type": "water_leakage",
            "description": "Leaking pipe near bus stop without requiring login",
            "address": "Public Bus Stop, Indore",
        },
    )
    assert submit_resp.status_code == 201
    ref = submit_resp.json()["reference_id"]

    # Check public status tracking
    track_resp = client.get(f"/api/v1/complaints/{ref}")
    assert track_resp.status_code == 200
    assert track_resp.json()["reference_id"] == ref
