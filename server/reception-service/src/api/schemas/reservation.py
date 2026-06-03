"""Schemas for reservation endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.api.schemas.guest import PHONE_REGEX
from src.domain.enums import ReservationStatus


class ReservationCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., pattern=PHONE_REGEX)
    passport_number: str | None = Field(default=None, max_length=40)
    room_id: uuid.UUID
    check_in_date: date
    check_out_date: date

    @model_validator(mode="after")
    def _date_order(self) -> Self:
        if self.check_out_date <= self.check_in_date:
            raise ValueError("check_out_date must be after check_in_date")
        return self


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    phone: str
    passport_number: str | None = None
    room_id: uuid.UUID
    room_number: int
    floor: int
    check_in_date: date
    check_out_date: date
    status: ReservationStatus
    nightly_rate_locked_minor_units: int
    guest_id: uuid.UUID | None = None
    status_changed_at: datetime
    created_at: datetime


class ReservationCheckInRequest(BaseModel):
    """Optional override of cleaning preference at check-in time."""

    cleaning_preference: str | None = Field(default=None, max_length=16)
    cleaning_preference_note: str | None = Field(default=None, max_length=200)
