"""Schemas for the room-service order API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.enums import OrderStatus


class OrderItem(BaseModel):
    """One line of an order. Price is in minor units (e.g. tiyin / cents)
    so float drift never reaches the bill."""

    name: str = Field(..., min_length=1, max_length=64)
    qty: int = Field(..., ge=1, le=99)
    price_minor_units: int = Field(..., ge=1)


class OrderCreate(BaseModel):
    """What reception staff submit when a guest orders from the menu."""

    guest_id: uuid.UUID
    items: list[OrderItem] = Field(..., min_length=1, max_length=20)

    @field_validator("items")
    @classmethod
    def at_least_one_item(cls, v: list[OrderItem]) -> list[OrderItem]:
        if not v:
            raise ValueError("order must have at least one item")
        return v


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    guest_id: uuid.UUID
    room_id: uuid.UUID
    room_number: int
    floor: int
    status: OrderStatus
    items: list[dict]
    total_minor_units: int
    taken_by_user_id: uuid.UUID
    received_at: datetime
    preparing_at: datetime | None = None
    delivering_at: datetime | None = None
    delivered_at: datetime | None = None
