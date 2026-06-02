"""Read-only schemas surfaced by the room-service kitchen API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.domain.enums import OrderStatus


class OrderMirrorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    guest_id: uuid.UUID
    room_number: int
    floor: int
    status: OrderStatus
    items: list[dict]
    total_minor_units: int
    received_at: datetime
    preparing_at: datetime | None = None
    delivering_at: datetime | None = None
    delivered_at: datetime | None = None
