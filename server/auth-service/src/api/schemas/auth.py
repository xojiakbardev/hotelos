"""Auth-related request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.core.constants import PHONE_REGEX
from src.domain.enums import UserRole


class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=PHONE_REGEX, examples=["+998901111111"])
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str
    phone: str
    full_name: str | None = None


class MeResponse(BaseModel):
    id: str
    phone: str
    full_name: str | None
    role: UserRole
    is_active: bool
