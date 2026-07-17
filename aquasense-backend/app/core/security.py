"""Security, password hashing, JWT authentication, and authority authorization dependencies."""

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models.authority_user import AuthorityUser

# Password hasher configured with Argon2
password_hash = PasswordHash((Argon2Hasher(),))

# OAuth2 scheme without auto_error so we can return consistent custom HTTP errors
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/authority/login",
    auto_error=False,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using secure Argon2 algorithm."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2 hash."""
    return password_hash.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> None:
    """Validate prototype password requirements (min 4 chars)."""
    if not password or len(password) < 4:
        raise ValueError("Password must be at least 4 characters long.")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token signed with the configured secret and algorithm."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def get_current_authority(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthorityUser:
    """FastAPI dependency to authenticate and retrieve the current active AuthorityUser."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(user_id_str)
    except (jwt.InvalidTokenError, jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(AuthorityUser).filter(AuthorityUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive account",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
