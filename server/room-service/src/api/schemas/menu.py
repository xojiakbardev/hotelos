"""Schemas for the menu CRUD API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MenuItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    category: str = Field("other", max_length=32)
    price_minor_units: int = Field(..., ge=1)
    prep_minutes: int = Field(10, ge=1, le=240)


class MenuItemCreate(MenuItemBase):
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    category: str | None = Field(default=None, max_length=32)
    price_minor_units: int | None = Field(default=None, ge=1)
    prep_minutes: int | None = Field(default=None, ge=1, le=240)
    is_available: bool | None = None


class AvailabilityUpdate(BaseModel):
    """Explicit body for the dedicated availability toggle endpoint."""

    is_available: bool


class MenuItemOut(MenuItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_available: bool
    created_at: datetime
    updated_at: datetime
