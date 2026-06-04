"""Pydantic schemas for the guest self-service portal."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class GuestOrderCreate(BaseModel):
    """Guest submits a food order from menu."""
    items: list[dict] = Field(
        ...,
        min_length=1,
        description='[{"menu_item_id": "uuid", "name": "...", "qty": 1, "price_minor_units": 500}]',
    )


class GuestMaintenanceCreate(BaseModel):
    """Guest reports a maintenance issue."""
    description: str = Field(..., min_length=5, max_length=500)


class GuestCleaningCreate(BaseModel):
    """Guest requests room cleaning."""
    priority: str = Field(default="normal", pattern=r"^(low|normal|high)$")
    preferred_time: str = Field(default="afternoon", pattern=r"^(morning|afternoon|evening|now)$")
    note: str | None = Field(default=None, max_length=200)


class GuestOrderOut(BaseModel):
    id: uuid.UUID
    status: str
    items: list[dict]
    total_minor_units: int
    received_at: datetime
    preparing_at: datetime | None = None
    delivering_at: datetime | None = None
    delivered_at: datetime | None = None


class GuestMaintenanceOut(BaseModel):
    id: uuid.UUID
    description: str
    status: str
    urgency: str
    reported_at: datetime
    assigned_at: datetime | None = None
    resolved_at: datetime | None = None


class GuestCleaningOut(BaseModel):
    id: uuid.UUID
    priority: str
    preferred_time: str
    note: str | None = None
    status: str
    requested_at: datetime
    completed_at: datetime | None = None


class GuestDashboardOut(BaseModel):
    guest_name: str
    room_number: int
    floor: int
    orders: list[GuestOrderOut]
    maintenance_requests: list[GuestMaintenanceOut]
    cleaning_requests: list[GuestCleaningOut]
