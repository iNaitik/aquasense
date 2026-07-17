#!/usr/bin/env python3
"""CLI utility to securely bootstrap an Authority user for AQUA-SENSE Prototype 1.

Usage:
    python scripts/create_authority_user.py
    python scripts/create_authority_user.py --name "Admin" --email "admin@aquasense.org" --password "SecurePass123"
"""

import argparse
import getpass
import sys
import os

# Add parent directory to python path so we can import app modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.authority_user import AuthorityUser
from app.core.security import hash_password, validate_password_strength


def create_authority_user(name: str | None = None, email: str | None = None, password: str | None = None) -> None:
    db: Session = SessionLocal()
    try:
        if not name:
            name = input("Enter Authority User Name: ").strip()
            while not name:
                print("Error: Name cannot be empty.")
                name = input("Enter Authority User Name: ").strip()

        if not email:
            email = input("Enter Authority User Email: ").strip().lower()
            while not email or "@" not in email:
                print("Error: Please enter a valid email address.")
                email = input("Enter Authority User Email: ").strip().lower()
        else:
            email = email.strip().lower()

        # Check for existing user
        existing = db.query(AuthorityUser).filter(AuthorityUser.email == email).first()
        if existing:
            print(f"Error: An authority account with email '{email}' already exists.")
            sys.exit(1)

        if not password:
            while True:
                password = getpass.getpass("Enter secure password: ")
                try:
                    validate_password_strength(password)
                except ValueError as e:
                    print(f"Error: {e}")
                    continue

                confirm = getpass.getpass("Confirm password: ")
                if password != confirm:
                    print("Error: Passwords do not match. Try again.")
                else:
                    break
        else:
            try:
                validate_password_strength(password)
            except ValueError as e:
                print(f"Error validating supplied password: {e}")
                sys.exit(1)

        hashed = hash_password(password)
        new_user = AuthorityUser(
            name=name,
            email=email,
            hashed_password=hashed,
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        print(f"Successfully created authority user: {new_user.name} ({new_user.email}) [ID: {new_user.id}]")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a secure Authority User account.")
    parser.add_argument("--name", help="Full name of the authority official")
    parser.add_argument("--email", help="Unique email address for login")
    parser.add_argument("--password", help="Account password (min 8 chars, 1 letter, 1 number)")
    args = parser.parse_args()

    create_authority_user(args.name, args.email, args.password)


if __name__ == "__main__":
    main()
