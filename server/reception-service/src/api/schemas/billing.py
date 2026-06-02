"""Schemas surfaced by the check-out endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class CheckOutResponse(BaseModel):
    guest_id: uuid.UUID
    room_number: int
    bill_id: uuid.UUID
    nights: int
    nightly_rate_minor_units: int
    room_cost_minor_units: int
    room_service_charges_minor_units: int
    extras_minor_units: int
    discount_minor_units: int
    total_minor_units: int
    finalized_at: datetime
    checked_out_at: datetime
