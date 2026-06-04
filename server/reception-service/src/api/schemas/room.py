"""Pydantic schemas for room-related API surface."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import Cleanliness, Proximity, RoomStatus, RoomType


class RoomOut(BaseModel):
    """A single room row as it appears on the dashboard.

    `id` is typed as UUID so Pydantic serialises it to its standard string
    form on the JSON boundary — clients receive a plain string, never a
    Python repr.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    room_number: int
    floor: int
    room_type: RoomType
    proximity: Proximity
    cleanliness_status: Cleanliness
    status: RoomStatus
    nightly_rate_minor_units: int
    freshness_score: float = 1.0
    dynamic_price_minor_units: int = 0
    last_cleaned_at: datetime
    last_assigned_at: datetime | None = None


class RoomList(BaseModel):
    """Wrapper so the list response can grow new top-level fields later
    (counts, filters) without breaking the client contract."""

    rooms: list[RoomOut]
    total: int = Field(..., description="number of rooms returned")


class RoomCreate(BaseModel):
    room_number: int = Field(..., ge=1, le=9999)
    floor: int = Field(..., ge=1, le=99)
    room_type: RoomType
    proximity: Proximity
    nightly_rate_minor_units: int = Field(..., ge=1)


class RoomUpdate(BaseModel):
    """All fields optional — manager edits a single field at a time."""

    floor: int | None = Field(default=None, ge=1, le=99)
    room_type: RoomType | None = None
    proximity: Proximity | None = None
    nightly_rate_minor_units: int | None = Field(default=None, ge=1)


class RoomBulkCreate(BaseModel):
    rooms: list[RoomCreate]

