"""User CRUD request and response schemas (manager-only endpoints)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.core.constants import PHONE_REGEX
from src.domain.enums import UserRole


class UserCreate(BaseModel):
    phone: str = Field(..., pattern=PHONE_REGEX)
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole
    full_name: str | None = Field(default=None, max_length=120)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    role: UserRole | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    is_active: bool | None = None


class UserOut(BaseModel):
    id: str
    phone: str
    full_name: str | None
    role: UserRole
    is_active: bool
