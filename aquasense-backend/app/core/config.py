"""AQUA-SENSE backend – core configuration."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/aquasense"
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    PIPELINE_MATCH_MAX_DISTANCE_M: float = 500.0
    SECRET_KEY: str = "aquasense-secret-jwt-key-prototype-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ---- Notifications ----
    NOTIFICATIONS_ENABLED: bool = True
    NOTIFICATION_PROVIDER: str = "console"  # "console", "msg91", or "twilio"

    # MSG91 Provider Configuration
    MSG91_AUTH_KEY: Optional[str] = None
    MSG91_TEMPLATE_ID: Optional[str] = None
    MSG91_TEMPLATE_ID_SUBMITTED: Optional[str] = None
    MSG91_TEMPLATE_ID_REVIEWED: Optional[str] = None
    MSG91_TEMPLATE_ID_ASSIGNED: Optional[str] = None
    MSG91_TEMPLATE_ID_RESOLVED: Optional[str] = None
    MSG91_SENDER_ID: Optional[str] = None

    # Twilio Provider Configuration
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None


settings = Settings()
