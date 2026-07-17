# AQUA-SENSE SMS Notification Setup & MSG91 Integration Guide

This guide explains how to configure, test, and maintain the SMS notification system in AQUA-SENSE Prototype 1. The architecture supports two operational modes: a local/development `console` mode and a production transactional SMS mode using the **MSG91 Flow v5 API**.

---

## 1. Overview & Architecture

AQUA-SENSE keeps citizens informed about their water issues across four key lifecycle events:
1. **Complaint Submitted (`complaint_submitted`)**: Sent immediately when a citizen reports an issue.
2. **Complaint Reviewed (`complaint_reviewed`)**: Sent when the Authority marks the issue as under review.
3. **Complaint Assigned (`complaint_assigned`)**: Sent when field engineers are assigned.
4. **Complaint Resolved (`complaint_resolved`)**: Sent once the issue is marked fixed.

### Failure Isolation Architecture
To ensure high system reliability, SMS sending is **decoupled and failure-isolated** from the primary database transactions. Even if the SMS provider experiences network timeouts (`httpx.TimeoutException`) or returns an API error (`401/422/500`), the complaint submission or status update **will always succeed**. The failed notification is recorded in the `notifications` database table (`status = "failed"`) along with the provider error message so that it can be retried cleanly later.

---

## 2. Environment Variables & Configuration

Configure notification behavior in the backend `.env` file (see `.env.example`):

| Variable | Default | Description |
| :--- | :--- | :--- |
| `NOTIFICATIONS_ENABLED` | `true` | Master switch (`true`/`false`). When `false`, no notifications are generated or sent. |
| `NOTIFICATION_PROVIDER` | `console` | Set to `console` for local development, `msg91` for MSG91 Flow, or `twilio` for Twilio SMS. |
| `MSG91_AUTH_KEY` | *(empty)* | MSG91 API Authentication Key (found in your MSG91 dashboard). Required if `msg91` is selected. |
| `MSG91_TEMPLATE_ID` | *(empty)* | Default/fallback DLT-approved Flow Template ID for all events. |
| `MSG91_TEMPLATE_ID_SUBMITTED` | *(empty)* | Specific DLT Template ID for `complaint_submitted` event. |
| `MSG91_TEMPLATE_ID_REVIEWED` | *(empty)* | Specific DLT Template ID for `complaint_reviewed` event. |
| `MSG91_TEMPLATE_ID_ASSIGNED` | *(empty)* | Specific DLT Template ID for `complaint_assigned` event. |
| `MSG91_TEMPLATE_ID_RESOLVED` | *(empty)* | Specific DLT Template ID for `complaint_resolved` event. |
| `MSG91_SENDER_ID` | *(empty)* | Optional 6-character DLT Sender ID / Shortcode (e.g., `AQASNS`). |
| `TWILIO_ACCOUNT_SID` | *(empty)* | Twilio Account SID (found on your Twilio console dashboard). Required if `twilio` is selected. |
| `TWILIO_AUTH_TOKEN` | *(empty)* | Twilio Auth Token. Required if `twilio` is selected. |
| `TWILIO_FROM_NUMBER` | *(empty)* | Twilio Sender Phone Number (E.164 format, e.g., `+1626460357`). Required if `twilio` is selected. |

---

## 3. Local Development (`console` mode)

In local development, set `NOTIFICATION_PROVIDER=console` in your `.env` file:
```env
NOTIFICATIONS_ENABLED=true
NOTIFICATION_PROVIDER=console
```

When complaints are submitted or updated, the system will log the notification to the server console and application logs with the recipient's phone number safely masked (for privacy protection):
```
--- SMS notification generated ---
Recipient: +91******3210
Event: complaint_submitted
Message: Your AQUA-SENSE complaint AQS-2026-0001 has been submitted successfully. You can use this reference number to track your complaint.
Provider Message ID: console_be6ac4f0
----------------------------------
```

---

## 4. Production MSG91 & DLT Setup (India)

In India, all transactional SMS must adhere to **TRAI DLT (Distributed Ledger Technology)** regulations:
1. **Register on DLT Platform**: Register your organization and get your Entity ID and Sender ID (`MSG91_SENDER_ID`).
2. **Create Flow Templates in MSG91**:
   - Create a transactional Flow template for each of the 4 lifecycle events.
   - Include variable placeholders (e.g., `##reference_id##` or `##VAR1##`) in your template text where the complaint reference number (`AQS-XXXX-XXXX`) will be injected.
3. **Configure `.env`**:
   ```env
   NOTIFICATIONS_ENABLED=true
   NOTIFICATION_PROVIDER=msg91
   MSG91_AUTH_KEY=your_real_msg91_auth_key_here
   MSG91_TEMPLATE_ID_SUBMITTED=flow_template_id_for_submission
   MSG91_TEMPLATE_ID_REVIEWED=flow_template_id_for_review
   MSG91_TEMPLATE_ID_ASSIGNED=flow_template_id_for_assignment
   MSG91_TEMPLATE_ID_RESOLVED=flow_template_id_for_resolution
   MSG91_SENDER_ID=AQASNS
   ```

When triggered, the backend sends a POST request to `https://control.msg91.com/api/v5/flow/` containing the recipient's normalized mobile number (`91XXXXXXXXXX`) and variables dictionary.

---

## 4.1 Production Twilio Setup (`twilio` mode)

To send transactional SMS globally or via your verified **Twilio** account using the official Twilio Python SDK (`twilio>=8.0.0`):

1. **Obtain Twilio Credentials**: Locate your **Account SID** and **Auth Token** on the Twilio Console homepage.
2. **Obtain a Twilio Phone Number**: Ensure you have an SMS-capable Twilio phone number (`TWILIO_FROM_NUMBER`).
3. **Configure `.env`**:
   ```env
   NOTIFICATIONS_ENABLED=true
   NOTIFICATION_PROVIDER=twilio
   TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_FROM_NUMBER=+1626460357
   ```

When triggered, the backend uses `client.messages.create(body=message, from_=TWILIO_FROM_NUMBER, to=recipient)` via the official Twilio SDK. Upon success, the returned Twilio Message SID (`SMxxxx...`) is stored in the `notifications` table as `provider_message_id`. If an exception occurs, sensitive credentials and phone numbers are automatically redacted before saving to the database error logs.

---

## 5. Maintenance: Retrying Failed Notifications

If SMS delivery fails (e.g., due to temporary network issues or MSG91 outages), the notification status is stored as `failed` in the database.

You can inspect notification metadata securely from the Authority Portal API:
```http
GET /api/v1/admin/complaints/{reference_id}/notifications
Authorization: Bearer <authority_jwt_token>
```
*(Returns safe metadata including `status`, `error_message`, and `masked_recipient` without exposing sensitive phone digits).*

### Retry Script
To retry all failed notifications across the database without creating duplicates, run the maintenance CLI utility:
```powershell
# Retry all failed notifications across the database
python scripts/retry_failed_notifications.py --all

# Retry a specific notification by its database ID
python scripts/retry_failed_notifications.py --notification-id 15
```

---

## 6. Privacy & Security Best Practices

- **Never hardcode API keys**: Always supply `MSG91_AUTH_KEY` via environment variables.
- **Masking Enforcement**: Citizen phone numbers (`phone_number`) are automatically masked (`+91******3210`) in console logs and authority history endpoints via `mask_phone_number()`.
- **Public API Isolation**: Public citizen tracking endpoints (`GET /api/v1/complaints/{reference_id}`) do not expose notification records or recipient details.
