"""Notification service layer.

Manages notification lifecycle: duplicate protection, provider dispatch,
persistence, and failure isolation for citizen complaint updates.
"""

from datetime import datetime, timezone
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.complaint import Complaint
from app.models.notification import Notification
from app.services.notification_providers import (
    ConsoleNotificationProvider,
    MSG91NotificationProvider,
    NotificationProvider,
    TwilioNotificationProvider,
)
from app.utils.phone import mask_phone_number

logger = logging.getLogger(__name__)


def get_notification_provider() -> NotificationProvider:
    """Return the active SMS notification provider based on application settings."""
    provider_name = settings.NOTIFICATION_PROVIDER.lower().strip()
    if provider_name == "console":
        return ConsoleNotificationProvider()
    if provider_name == "msg91":
        return MSG91NotificationProvider()
    if provider_name == "twilio":
        return TwilioNotificationProvider()
    raise ValueError(
        f"Unknown notification provider configured: '{settings.NOTIFICATION_PROVIDER}'. "
        "Must be one of: console, msg91, twilio."
    )


def send_complaint_notification(
    db: Session,
    complaint: Complaint,
    event_type: str,
    message: str,
    variables: Optional[dict[str, str]] = None,
) -> Optional[Notification]:
    """Trigger an SMS notification for a complaint event safely.

    Handles duplicate checks and catches provider errors to ensure core
    database workflows (complaint submission or status transition) never fail.
    """
    if not settings.NOTIFICATIONS_ENABLED:
        logger.debug(
            f"Notifications disabled. Skipping '{event_type}' for complaint {complaint.reference_id}."
        )
        return None

    if not complaint.phone_number:
        logger.warning(
            f"Complaint {complaint.reference_id} has no phone_number. Skipping SMS notification."
        )
        return None

    # Duplicate protection: check if a notification already exists for this (complaint_id, event_type)
    existing: Optional[Notification] = (
        db.query(Notification)
        .filter(
            Notification.complaint_id == complaint.id,
            Notification.event_type == event_type,
        )
        .first()
    )
    if existing is not None:
        logger.info(
            f"Notification already exists for complaint {complaint.reference_id} event '{event_type}'. Skipping duplicate."
        )
        return existing

    notification = Notification(
        complaint_id=complaint.id,
        channel="sms",
        event_type=event_type,
        recipient=complaint.phone_number,
        message=message,
        status="pending",
        provider=settings.NOTIFICATION_PROVIDER,
    )
    db.add(notification)
    try:
        db.flush()
    except Exception as exc:
        logger.error(
            f"Could not flush pending notification record for {complaint.reference_id}: {exc}"
        )
        return None

    vars_map = {"reference_id": complaint.reference_id}
    if variables:
        vars_map.update(variables)

    try:
        provider = get_notification_provider()
        success, msg_id, err_msg = provider.send_sms(
            phone_number=complaint.phone_number,
            message=message,
            variables=vars_map,
            event_type=event_type,
        )
    except Exception as exc:
        success, msg_id, err_msg = False, None, f"Unhandled provider exception: {exc}"

    if success:
        notification.status = "sent"
        notification.provider_message_id = msg_id
        notification.sent_at = datetime.now(timezone.utc)
        notification.error_message = None
    else:
        notification.status = "failed"
        notification.error_message = err_msg
        masked = mask_phone_number(complaint.phone_number)
        logger.warning(
            f"SMS delivery failed for {masked} (complaint {complaint.reference_id}, event {event_type}): {err_msg}"
        )

    try:
        db.flush()
    except Exception as exc:
        logger.error(
            f"Could not flush final notification state for {complaint.reference_id}: {exc}"
        )

    return notification


def retry_failed_notification(db: Session, notification: Notification) -> bool:
    """Retry sending an existing failed notification.

    Returns True if delivery succeeded, False otherwise. Does not create duplicate records.
    """
    if notification.status != "failed":
        return False

    vars_map = {"reference_id": notification.complaint.reference_id} if notification.complaint else {}

    try:
        provider = get_notification_provider()
        success, msg_id, err_msg = provider.send_sms(
            phone_number=notification.recipient,
            message=notification.message,
            variables=vars_map,
            event_type=notification.event_type,
        )
    except Exception as exc:
        success, msg_id, err_msg = False, None, f"Unhandled retry exception: {exc}"

    if success:
        notification.status = "sent"
        notification.provider_message_id = msg_id
        notification.sent_at = datetime.now(timezone.utc)
        notification.error_message = None
        db.flush()
        return True
    else:
        notification.error_message = err_msg
        db.flush()
        return False
