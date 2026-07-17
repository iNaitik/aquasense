"""Tests for SMS Complaint Notifications (Step 8).

Covers (Section 18 & Plan):
- Complaint submission triggers submitted notification.
- Status transitions trigger corresponding notifications.
- No-op updates and idempotency prevent duplicate notifications.
- Failure isolation: SMS failure never breaks complaint submission or status update.
- Retry utility retries failed notifications without creating duplicates.
- Notifications disabled switch behaves consistently.
- Privacy masking and JWT protection on authority notification history endpoint.
"""

from unittest.mock import MagicMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models.complaint import Complaint, ComplaintStatus
from app.models.complaint_status_history import ComplaintStatusHistory
from app.models.notification import Notification
from app.services.notification_service import get_notification_provider, retry_failed_notification
from app.services.notification_providers import (
    ConsoleNotificationProvider,
    MSG91NotificationProvider,
    TwilioNotificationProvider,
)
from app.core.config import settings

client = TestClient(app)


@pytest.fixture(scope="function")
def cleanup_notifications():
    """Clean up test complaints and notifications created during test execution."""
    yield
    db: Session = SessionLocal()
    try:
        complaints = db.query(Complaint).filter(Complaint.citizen_name.like("SMS Test%")).all()
        for c in complaints:
            db.query(Notification).filter_by(complaint_id=c.id).delete()
            db.query(ComplaintStatusHistory).filter_by(complaint_id=c.id).delete()
            db.delete(c)
        db.commit()
    finally:
        db.close()


def create_test_complaint(name="SMS Test Citizen", phone="+919876543210", issue_type="water_leakage") -> dict:
    resp = client.post(
        "/api/v1/complaints",
        data={
            "citizen_name": name,
            "phone_number": phone,
            "issue_type": issue_type,
            "description": "Testing SMS notifications workflow",
            "latitude": "22.7245",
            "longitude": "75.8436",
            "address": "Test Street Indore",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_complaint_submission_creates_submitted_notification(cleanup_notifications):
    """Verify complaint submission creates a complaint_submitted notification."""
    data = create_test_complaint()
    ref_id = data["reference_id"]

    db: Session = SessionLocal()
    try:
        complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
        assert complaint is not None
        notifs = db.query(Notification).filter_by(complaint_id=complaint.id).all()
        assert len(notifs) == 1
        n = notifs[0]
        assert n.event_type == "complaint_submitted"
        assert n.channel == "sms"
        assert n.status == "sent"
        assert n.recipient == "+919876543210"
        assert n.provider_message_id is not None
    finally:
        db.close()


def test_status_update_creates_notifications(auth_headers, cleanup_notifications):
    """Verify authority lifecycle transitions generate corresponding notifications."""
    data = create_test_complaint()
    ref_id = data["reference_id"]

    # submitted -> reviewed
    resp = client.patch(
        f"/api/v1/admin/complaints/{ref_id}/status",
        json={"status": "reviewed"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # reviewed -> assigned
    resp = client.patch(
        f"/api/v1/admin/complaints/{ref_id}/status",
        json={"status": "assigned"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # assigned -> resolved
    resp = client.patch(
        f"/api/v1/admin/complaints/{ref_id}/status",
        json={"status": "resolved"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    db: Session = SessionLocal()
    try:
        complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
        notifs = (
            db.query(Notification)
            .filter_by(complaint_id=complaint.id)
            .order_by(Notification.created_at.asc())
            .all()
        )
        assert len(notifs) == 4
        events = [n.event_type for n in notifs]
        assert events == [
            "complaint_submitted",
            "complaint_reviewed",
            "complaint_assigned",
            "complaint_resolved",
        ]
        for n in notifs:
            assert n.status == "sent"
    finally:
        db.close()


def test_noop_status_update_does_not_create_duplicate(auth_headers, cleanup_notifications):
    """Verify calling update_status with the current status is a no-op and creates no duplicate notification."""
    data = create_test_complaint()
    ref_id = data["reference_id"]

    # Same status call
    resp = client.patch(
        f"/api/v1/admin/complaints/{ref_id}/status",
        json={"status": "submitted"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    db: Session = SessionLocal()
    try:
        complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
        notifs = db.query(Notification).filter_by(complaint_id=complaint.id).all()
        assert len(notifs) == 1  # Only the original complaint_submitted notification exists
    finally:
        db.close()


def test_sms_failure_does_not_fail_complaint_submission(cleanup_notifications):
    """Verify complaint submission succeeds even if SMS provider raises an exception."""
    with patch("app.services.notification_providers.ConsoleNotificationProvider.send_sms", side_effect=httpx.TimeoutException("Provider timeout")):
        resp = client.post(
            "/api/v1/complaints",
            data={
                "citizen_name": "SMS Test Timeout",
                "phone_number": "+919876543210",
                "issue_type": "other",
                "description": "Complaint during SMS outage",
                "latitude": "22.7245",
                "longitude": "75.8436",
                "address": "Timeout Street",
            },
        )
        assert resp.status_code == 201
        ref_id = resp.json()["reference_id"]

        db: Session = SessionLocal()
        try:
            complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
            assert complaint is not None
            notifs = db.query(Notification).filter_by(complaint_id=complaint.id).all()
            assert len(notifs) == 1
            assert notifs[0].status == "failed"
            assert "Provider timeout" in notifs[0].error_message
        finally:
            db.close()


def test_sms_failure_does_not_fail_status_update(auth_headers, cleanup_notifications):
    """Verify status transition succeeds even if SMS provider fails during update."""
    data = create_test_complaint(name="SMS Test Status Outage")
    ref_id = data["reference_id"]

    with patch("app.services.notification_providers.ConsoleNotificationProvider.send_sms", return_value=(False, None, "Provider error 500")):
        resp = client.patch(
            f"/api/v1/admin/complaints/{ref_id}/status",
            json={"status": "reviewed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["current_status"] == "reviewed"

        db: Session = SessionLocal()
        try:
            complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
            notifs = db.query(Notification).filter_by(complaint_id=complaint.id, event_type="complaint_reviewed").all()
            assert len(notifs) == 1
            assert notifs[0].status == "failed"
            assert "Provider error 500" in notifs[0].error_message
        finally:
            db.close()


def test_retry_script_updates_existing_notification(cleanup_notifications):
    """Verify retrying a failed notification updates its status to sent without creating duplicate records."""
    # Create complaint where SMS fails initially
    with patch("app.services.notification_providers.ConsoleNotificationProvider.send_sms", return_value=(False, None, "Initial network failure")):
        data = create_test_complaint(name="SMS Test Retry")
        ref_id = data["reference_id"]

    db: Session = SessionLocal()
    try:
        complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
        notifs_before = db.query(Notification).filter_by(complaint_id=complaint.id).all()
        assert len(notifs_before) == 1
        assert notifs_before[0].status == "failed"

        # Now retry the failed notification without mock error
        success = retry_failed_notification(db, notifs_before[0])
        db.commit()
        assert success is True

        notifs_after = db.query(Notification).filter_by(complaint_id=complaint.id).all()
        assert len(notifs_after) == 1  # No duplicate record created!
        assert notifs_after[0].status == "sent"
        assert notifs_after[0].error_message is None
    finally:
        db.close()


def test_duplicate_event_notification_prevention(cleanup_notifications):
    """Verify database constraints and idempotency checks prevent duplicate notification records."""
    data = create_test_complaint(name="SMS Test Idempotent")
    ref_id = data["reference_id"]

    db: Session = SessionLocal()
    try:
        complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
        notif_count = db.query(Notification).filter_by(complaint_id=complaint.id, event_type="complaint_submitted").count()
        assert notif_count == 1

        # Triggering notification service again explicitly should return existing without adding new row
        from app.services.notification_service import send_complaint_notification
        send_complaint_notification(db, complaint, "complaint_submitted", "Test message")
        db.commit()

        notif_count_after = db.query(Notification).filter_by(complaint_id=complaint.id, event_type="complaint_submitted").count()
        assert notif_count_after == 1
    finally:
        db.close()


def test_notifications_disabled_behavior(cleanup_notifications):
    """Verify setting NOTIFICATIONS_ENABLED=False disables notification creation and sending."""
    original_setting = settings.NOTIFICATIONS_ENABLED
    try:
        settings.NOTIFICATIONS_ENABLED = False
        data = create_test_complaint(name="SMS Test Disabled")
        ref_id = data["reference_id"]

        db: Session = SessionLocal()
        try:
            complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
            notifs = db.query(Notification).filter_by(complaint_id=complaint.id).all()
            assert len(notifs) == 0
        finally:
            db.close()
    finally:
        settings.NOTIFICATIONS_ENABLED = original_setting


def test_privacy_masking_and_protected_endpoint(auth_headers, cleanup_notifications):
    """Verify authority notification history requires JWT, returns masked phone numbers, and citizen API exposes none."""
    data = create_test_complaint(name="SMS Test Privacy", phone="+919876543210")
    ref_id = data["reference_id"]

    # 1. Unauthenticated request must return 401
    resp_unauth = client.get(f"/api/v1/admin/complaints/{ref_id}/notifications")
    assert resp_unauth.status_code == 401

    # 2. Authenticated authority request returns metadata with masked phone number
    resp_auth = client.get(
        f"/api/v1/admin/complaints/{ref_id}/notifications",
        headers=auth_headers,
    )
    assert resp_auth.status_code == 200
    notifs = resp_auth.json()
    assert len(notifs) == 1
    assert notifs[0]["masked_recipient"] == "+91******3210"
    assert "phone_number" not in notifs[0]
    assert "recipient" not in notifs[0]

    # 3. Public citizen tracking endpoint should not expose notification records
    resp_public = client.get(f"/api/v1/complaints/{ref_id}")
    assert resp_public.status_code == 200
    public_data = resp_public.json()
    assert "notifications" not in public_data
    assert "phone_number" not in public_data


def test_get_notification_provider_selection_and_unknown_handling():
    """Verify correct provider class selection based on NOTIFICATION_PROVIDER setting and safety on unknown provider."""
    original_provider = settings.NOTIFICATION_PROVIDER
    try:
        settings.NOTIFICATION_PROVIDER = "console"
        assert isinstance(get_notification_provider(), ConsoleNotificationProvider)

        settings.NOTIFICATION_PROVIDER = "msg91"
        assert isinstance(get_notification_provider(), MSG91NotificationProvider)

        settings.NOTIFICATION_PROVIDER = "twilio"
        assert isinstance(get_notification_provider(), TwilioNotificationProvider)

        settings.NOTIFICATION_PROVIDER = "unknown_sms_provider"
        with pytest.raises(ValueError, match="Unknown notification provider configured"):
            get_notification_provider()
    finally:
        settings.NOTIFICATION_PROVIDER = original_provider


def test_twilio_provider_success():
    """Verify TwilioNotificationProvider sends SMS via SDK and returns Message SID."""
    original_sid = settings.TWILIO_ACCOUNT_SID
    original_token = settings.TWILIO_AUTH_TOKEN
    original_from = settings.TWILIO_FROM_NUMBER
    try:
        settings.TWILIO_ACCOUNT_SID = "AC_test_sid_12345"
        settings.TWILIO_AUTH_TOKEN = "secret_test_token_abcdef"
        settings.TWILIO_FROM_NUMBER = "+15551234567"

        with patch("app.services.notification_providers.TwilioClient") as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_message = MagicMock()
            mock_message.sid = "SM99998888777766665555"
            mock_client_instance.messages.create.return_value = mock_message
            mock_client_cls.return_value = mock_client_instance

            provider = TwilioNotificationProvider()
            success, msg_id, err_msg = provider.send_sms(
                phone_number="+919876543210",
                message="Test Twilio notification",
            )

            assert success is True
            assert msg_id == "SM99998888777766665555"
            assert err_msg is None

            mock_client_cls.assert_called_once_with("AC_test_sid_12345", "secret_test_token_abcdef")
            mock_client_instance.messages.create.assert_called_once_with(
                body="Test Twilio notification",
                from_="+15551234567",
                to="+919876543210",
            )
    finally:
        settings.TWILIO_ACCOUNT_SID = original_sid
        settings.TWILIO_AUTH_TOKEN = original_token
        settings.TWILIO_FROM_NUMBER = original_from


def test_twilio_provider_failure_sanitization():
    """Verify Twilio exception is caught, marked failed, and error sanitized without credentials/digits."""
    original_sid = settings.TWILIO_ACCOUNT_SID
    original_token = settings.TWILIO_AUTH_TOKEN
    original_from = settings.TWILIO_FROM_NUMBER
    try:
        settings.TWILIO_ACCOUNT_SID = "AC_secret_account_sid"
        settings.TWILIO_AUTH_TOKEN = "super_secret_auth_token"
        settings.TWILIO_FROM_NUMBER = "+15550001111"

        with patch("app.services.notification_providers.TwilioClient") as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_instance.messages.create.side_effect = Exception(
                "Twilio error for AC_secret_account_sid and super_secret_auth_token when sending to +919876543210"
            )
            mock_client_cls.return_value = mock_client_instance

            provider = TwilioNotificationProvider()
            success, msg_id, err_msg = provider.send_sms(
                phone_number="+919876543210",
                message="Sensitive Twilio test",
            )

            assert success is False
            assert msg_id is None
            assert err_msg is not None
            assert "[REDACTED_SID]" in err_msg
            assert "[REDACTED_TOKEN]" in err_msg
            assert "+91******3210" in err_msg
            assert "AC_secret_account_sid" not in err_msg
            assert "super_secret_auth_token" not in err_msg
            assert "+919876543210" not in err_msg
    finally:
        settings.TWILIO_ACCOUNT_SID = original_sid
        settings.TWILIO_AUTH_TOKEN = original_token
        settings.TWILIO_FROM_NUMBER = original_from


def test_complaint_submission_succeeds_when_twilio_fails(cleanup_notifications):
    """Verify complaint submission succeeds and records failed notification when Twilio fails."""
    original_provider = settings.NOTIFICATION_PROVIDER
    original_sid = settings.TWILIO_ACCOUNT_SID
    original_token = settings.TWILIO_AUTH_TOKEN
    original_from = settings.TWILIO_FROM_NUMBER
    try:
        settings.NOTIFICATION_PROVIDER = "twilio"
        settings.TWILIO_ACCOUNT_SID = "AC_simulated_sid"
        settings.TWILIO_AUTH_TOKEN = "token_simulated"
        settings.TWILIO_FROM_NUMBER = "+15551234567"

        with patch("app.services.notification_providers.TwilioClient") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.messages.create.side_effect = RuntimeError("Simulated Twilio network outage")
            mock_client_cls.return_value = mock_instance

            resp = client.post(
                "/api/v1/complaints",
                data={
                    "citizen_name": "SMS Test Twilio Outage",
                    "phone_number": "+919876543210",
                    "issue_type": "low_pressure",
                    "description": "Complaint submitted during Twilio failure",
                    "latitude": "22.7245",
                    "longitude": "75.8436",
                    "address": "Indore Road",
                },
            )
            assert resp.status_code == 201
            ref_id = resp.json()["reference_id"]

            db: Session = SessionLocal()
            try:
                complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
                assert complaint is not None
                notifs = db.query(Notification).filter_by(complaint_id=complaint.id).all()
                assert len(notifs) == 1
                assert notifs[0].status == "failed"
                assert notifs[0].provider == "twilio"
                assert "Simulated Twilio network outage" in notifs[0].error_message
            finally:
                db.close()
    finally:
        settings.NOTIFICATION_PROVIDER = original_provider
        settings.TWILIO_ACCOUNT_SID = original_sid
        settings.TWILIO_AUTH_TOKEN = original_token
        settings.TWILIO_FROM_NUMBER = original_from


def test_status_update_succeeds_when_twilio_fails(auth_headers, cleanup_notifications):
    """Verify status transition succeeds when Twilio provider throws an exception during update."""
    data = create_test_complaint(name="SMS Test Twilio Status Outage")
    ref_id = data["reference_id"]

    original_provider = settings.NOTIFICATION_PROVIDER
    original_sid = settings.TWILIO_ACCOUNT_SID
    original_token = settings.TWILIO_AUTH_TOKEN
    original_from = settings.TWILIO_FROM_NUMBER
    try:
        settings.NOTIFICATION_PROVIDER = "twilio"
        settings.TWILIO_ACCOUNT_SID = "AC_sid_update"
        settings.TWILIO_AUTH_TOKEN = "token_update"
        settings.TWILIO_FROM_NUMBER = "+15551234567"

        with patch("app.services.notification_providers.TwilioClient") as mock_client_cls:
            mock_instance = MagicMock()
            mock_instance.messages.create.side_effect = Exception("Twilio 503 Service Unavailable")
            mock_client_cls.return_value = mock_instance

            resp = client.patch(
                f"/api/v1/admin/complaints/{ref_id}/status",
                json={"status": "reviewed"},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            assert resp.json()["current_status"] == "reviewed"

            db: Session = SessionLocal()
            try:
                complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
                notifs = db.query(Notification).filter_by(complaint_id=complaint.id, event_type="complaint_reviewed").all()
                assert len(notifs) == 1
                assert notifs[0].status == "failed"
                assert notifs[0].provider == "twilio"
                assert "Twilio 503 Service Unavailable" in notifs[0].error_message
            finally:
                db.close()
    finally:
        settings.NOTIFICATION_PROVIDER = original_provider
        settings.TWILIO_ACCOUNT_SID = original_sid
        settings.TWILIO_AUTH_TOKEN = original_token
        settings.TWILIO_FROM_NUMBER = original_from


def test_existing_console_provider_still_works(cleanup_notifications):
    """Verify that existing console provider behavior is preserved alongside Twilio/MSG91."""
    original_provider = settings.NOTIFICATION_PROVIDER
    try:
        settings.NOTIFICATION_PROVIDER = "console"
        data = create_test_complaint(name="SMS Test Console Preserve")
        ref_id = data["reference_id"]

        db: Session = SessionLocal()
        try:
            complaint = db.query(Complaint).filter_by(reference_id=ref_id).first()
            notifs = db.query(Notification).filter_by(complaint_id=complaint.id).all()
            assert len(notifs) == 1
            assert notifs[0].status == "sent"
            assert notifs[0].provider == "console"
            assert notifs[0].provider_message_id.startswith("console_")
        finally:
            db.close()
    finally:
        settings.NOTIFICATION_PROVIDER = original_provider
