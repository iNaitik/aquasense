"""Pydantic schemas for authority authentication and user profiles."""

from __future__ import annotations
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AuthorityLoginRequest(BaseModel):
    email: str = Field(..., description="Authority user email address")
    password: str = Field(..., description="Authority account password")


class AuthorityUserInfo(BaseModel):
    id: int
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    authority: AuthorityUserInfo
