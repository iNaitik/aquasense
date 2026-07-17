"""Notification provider abstractions and implementations.

Supports decoupled local development (ConsoleNotificationProvider) and
production transactional SMS sending via MSG91 Flow v5 API (MSG91NotificationProvider).
"""

from abc import ABC, abstractmethod
import logging
from typing import Optional
import uuid

import httpx
from twilio.rest import Client as TwilioClient

from app.core.config import settings
from app.utils.phone import mask_phone_number

logger = logging.getLogger(__name__)


class NotificationProvider(ABC):
    """Abstract base class for SMS notification providers."""

    @abstractmethod
    def send_sms(
        self,
        phone_number: str,
        message: str,
        template_id: Optional[str] = None,
        variables: Optional[dict[str, str]] = None,
        event_type: Optional[str] = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """Send an SMS notification to the recipient.

        Returns:
            tuple[bool, str | None, str | None]: (success, provider_message_id, error_message)
        """
        pass


class ConsoleNotificationProvider(NotificationProvider):
    """Development provider that logs safe masked notifications to console/logger."""

    def send_sms(
        self,
        phone_number: str,
        message: str,
        template_id: Optional[str] = None,
        variables: Optional[dict[str, str]] = None,
        event_type: Optional[str] = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        masked = mask_phone_number(phone_number)
        msg_id = f"console_{uuid.uuid4().hex[:8]}"

        log_msg = (
            f"\n--- SMS notification generated ---\n"
            f"Recipient: {masked}\n"
            f"Event: {event_type or 'unknown'}\n"
            f"Message: {message}\n"
            f"Provider Message ID: {msg_id}\n"
            f"----------------------------------"
        )
        logger.info(log_msg)
        print(log_msg)

        return True, msg_id, None


class MSG91NotificationProvider(NotificationProvider):
    """Production provider integrating with MSG91 Flow v5 API."""

    def __init__(self) -> None:
        self.api_url = "https://control.msg91.com/api/v5/flow/"

    def _get_template_for_event(
        self, event_type: Optional[str], explicit_template_id: Optional[str]
    ) -> Optional[str]:
        if explicit_template_id:
            return explicit_template_id

        if event_type == "complaint_submitted" and settings.MSG91_TEMPLATE_ID_SUBMITTED:
            return settings.MSG91_TEMPLATE_ID_SUBMITTED
        if event_type == "complaint_reviewed" and settings.MSG91_TEMPLATE_ID_REVIEWED:
            return settings.MSG91_TEMPLATE_ID_REVIEWED
        if event_type == "complaint_assigned" and settings.MSG91_TEMPLATE_ID_ASSIGNED:
            return settings.MSG91_TEMPLATE_ID_ASSIGNED
        if event_type == "complaint_resolved" and settings.MSG91_TEMPLATE_ID_RESOLVED:
            return settings.MSG91_TEMPLATE_ID_RESOLVED

        return settings.MSG91_TEMPLATE_ID

    def send_sms(
        self,
        phone_number: str,
        message: str,
        template_id: Optional[str] = None,
        variables: Optional[dict[str, str]] = None,
        event_type: Optional[str] = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        auth_key = settings.MSG91_AUTH_KEY
        if not auth_key or not auth_key.strip():
            return False, None, "MSG91_AUTH_KEY is not configured in settings"

        chosen_template_id = self._get_template_for_event(event_type, template_id)
        if not chosen_template_id or not chosen_template_id.strip():
            return False, None, f"MSG91 template ID not configured for event '{event_type}'"

        # MSG91 Flow expects digits without '+'
        mobiles = phone_number.lstrip("+").strip()

        recipient_payload: dict[str, str] = {"mobiles": mobiles}
        if variables:
            recipient_payload.update(variables)
        # Pass the full text message as well if template supports dynamic message var
        recipient_payload["message"] = message

        payload: dict[str, object] = {
            "template_id": chosen_template_id,
            "recipients": [recipient_payload],
        }
        if settings.MSG91_SENDER_ID:
            payload["shortcode"] = settings.MSG91_SENDER_ID

        headers = {
            "authkey": auth_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.api_url, json=payload, headers=headers)

            if response.status_code in (200, 202):
                try:
                    data = response.json()
                    if isinstance(data, dict) and data.get("type") == "error":
                        error_msg = str(data.get("message") or "Unknown MSG91 error")
                        return False, None, f"MSG91 rejected request: {error_msg}"
                    msg_id = str(
                        data.get("message")
                        if isinstance(data, dict)
                        else "msg91_accepted"
                    )
                    return True, msg_id, None
                except Exception:
                    return True, "msg91_accepted", None

            return (
                False,
                None,
                f"MSG91 HTTP error ({response.status_code}): {response.text[:200]}",
            )
        except httpx.TimeoutException:
            return False, None, "MSG91 request timed out after 10 seconds"
        except httpx.RequestError as exc:
            return False, None, f"MSG91 network request failed: {exc}"
        except Exception as exc:
            return False, None, f"Unexpected error while calling MSG91: {exc}"


class TwilioNotificationProvider(NotificationProvider):
    """Production provider integrating with official Twilio SMS API."""

    def send_sms(
        self,
        phone_number: str,
        message: str,
        template_id: Optional[str] = None,
        variables: Optional[dict[str, str]] = None,
        event_type: Optional[str] = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        from_number = settings.TWILIO_FROM_NUMBER

        if not account_sid or not auth_token or not from_number:
            return False, None, "Twilio credentials (SID, token, or from_number) are not configured in settings"

        try:
            client = TwilioClient(account_sid, auth_token)
            msg = client.messages.create(
                body=message,
                from_=from_number,
                to=phone_number,
            )
            return True, str(msg.sid), None
        except Exception as exc:
            masked_to = mask_phone_number(phone_number)
            error_msg = str(exc)
            if account_sid and account_sid in error_msg:
                error_msg = error_msg.replace(account_sid, "[REDACTED_SID]")
            if auth_token and auth_token in error_msg:
                error_msg = error_msg.replace(auth_token, "[REDACTED_TOKEN]")
            if phone_number and phone_number in error_msg:
                error_msg = error_msg.replace(phone_number, masked_to)

            return False, None, f"Twilio SMS delivery failed: {error_msg[:250]}"
