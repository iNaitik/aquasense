"""Shared pytest fixtures for AQUA-SENSE backend tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.authority_user import AuthorityUser
from app.core.security import hash_password, create_access_token
from app.main import app


@pytest.fixture(scope="function")
def db_session():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def auth_user(db_session: Session):
    """Ensure a test authority user exists and clean up afterwards."""
    email = "testauth@aquasense.org"
    user = db_session.query(AuthorityUser).filter(AuthorityUser.email == email).first()
    if not user:
        user = AuthorityUser(
            name="Test Inspector",
            email=email,
            hashed_password=hash_password("SecureTestPass1"),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    yield user
    db_session.query(AuthorityUser).filter(AuthorityUser.email == email).delete()
    db_session.commit()


@pytest.fixture(scope="function")
def auth_headers(auth_user: AuthorityUser):
    """Return standard Authorization Bearer header for valid authority access."""
    token = create_access_token({"sub": str(auth_user.id), "type": "authority"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function", autouse=True)
def force_console_notifications_during_tests():
    """Ensure automated tests use ConsoleNotificationProvider by default so external calls never occur."""
    from app.core.config import settings
    orig_provider = settings.NOTIFICATION_PROVIDER
    settings.NOTIFICATION_PROVIDER = "console"
    try:
        yield
    finally:
        settings.NOTIFICATION_PROVIDER = orig_provider
