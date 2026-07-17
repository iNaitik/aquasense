#!/usr/bin/env python3
"""CLI utility to retry failed SMS notifications in AQUA-SENSE without creating duplicates.

Usage:
    python scripts/retry_failed_notifications.py --all
    python scripts/retry_failed_notifications.py --notification-id 15
"""

import argparse
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.notification import Notification
from app.services.notification_service import retry_failed_notification
from app.utils.phone import mask_phone_number


def run_retry(all_failed: bool, notification_id: int | None) -> None:
    db: Session = SessionLocal()
    try:
        if notification_id is not None:
            notification = db.query(Notification).filter(Notification.id == notification_id).first()
            if not notification:
                print(f"[ERROR] Notification ID {notification_id} not found.")
                return
            if notification.status != "failed":
                print(f"[INFO] Notification ID {notification_id} is currently '{notification.status}' (not failed). Skipping.")
                return

            masked = mask_phone_number(notification.recipient)
            print(f"Retrying notification ID {notification.id} for recipient {masked}...")
            success = retry_failed_notification(db, notification)
            db.commit()
            if success:
                print(f"[SUCCESS] Notification ID {notification.id} successfully sent.")
            else:
                print(f"[FAILED] Notification ID {notification.id} delivery failed again: {notification.error_message}")
            return

        if all_failed:
            failed_list = db.query(Notification).filter(Notification.status == "failed").all()
            if not failed_list:
                print("[INFO] No failed notifications found in the database.")
                return

            print(f"Found {len(failed_list)} failed notifications. Starting retry...")
            succeeded_count = 0
            failed_count = 0
            for notification in failed_list:
                masked = mask_phone_number(notification.recipient)
                success = retry_failed_notification(db, notification)
                if success:
                    succeeded_count += 1
                    print(f"  [OK] ID {notification.id} ({masked}) -> Sent successfully.")
                else:
                    failed_count += 1
                    print(f"  [FAIL] ID {notification.id} ({masked}) -> {notification.error_message}")
            db.commit()
            print(f"\nSummary: Retried {len(failed_list)} notifications: {succeeded_count} succeeded, {failed_count} failed.")
            return

        print("[ERROR] Please specify either --all or --notification-id <ID>.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry failed SMS notifications.")
    parser.add_argument("--all", action="store_true", help="Retry all failed notifications.")
    parser.add_argument("--notification-id", type=int, help="Retry a specific notification ID.")
    args = parser.parse_args()

    if not args.all and args.notification_id is None:
        parser.print_help()
        sys.exit(1)

    run_retry(args.all, args.notification_id)


if __name__ == "__main__":
    main()
