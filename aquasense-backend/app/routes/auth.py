"""Authority authentication and profile API endpoints.

Prefix: /api/v1/auth/authority
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_current_authority, verify_password
from app.database import get_db
from app.models.authority_user import AuthorityUser
from app.schemas.auth import AuthorityLoginRequest, AuthorityUserInfo, TokenResponse

router = APIRouter(prefix="/api/v1/auth/authority", tags=["Authority Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate authority user and return access token",
)
def authority_login(
    body: AuthorityLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Validate email and password, and issue a Bearer JWT."""
    user = (
        db.query(AuthorityUser)
        .filter(AuthorityUser.email == body.email.strip().lower())
        .first()
    )
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive account",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    token = create_access_token(
        data={"sub": str(user.id), "type": "authority"},
        expires_delta=timedelta(seconds=expires_in),
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        authority=AuthorityUserInfo.model_validate(user),
    )


@router.get(
    "/me",
    response_model=AuthorityUserInfo,
    summary="Get current authenticated authority user profile",
)
def get_current_authority_me(
    current_user: AuthorityUser = Depends(get_current_authority),
) -> AuthorityUserInfo:
    """Verify stored token validity and return basic profile info."""
    return AuthorityUserInfo.model_validate(current_user)
