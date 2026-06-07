"""Pydantic schemas for guest / check-in / check-out endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.enums import CleaningPreference, Proximity, RoomType

PHONE_REGEX = r"^\+?[1-9]\d{9,14}$"


class CheckInRequest(BaseModel):
    """What reception staff submit when checking a guest in.

    Two modes:
      * Algorithm-driven — caller provides `room_type` (+ optional floor /
        proximity preferences) and reception's assignment algorithm picks
        the best matching room.
      * Direct — caller provides `room_id` (e.g. a receptionist clicked a
        specific available room card). The algorithm is bypassed; only the
        named room is locked. Other preferences are ignored.

    At least one of `room_id` or `room_type` is required.
    """

    full_name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., pattern=PHONE_REGEX, examples=["+998901234567"])
    passport_number: str | None = Field(default=None, max_length=40)
    nights: int = Field(..., ge=1, le=365, description="number of nights")

    room_id: uuid.UUID | None = None
    room_type: RoomType | None = None
    floor_preference: int | None = Field(default=None, ge=1, le=99)
    proximity_preference: Proximity | None = None
    cleaning_preference: CleaningPreference = CleaningPreference.AFTERNOON
    cleaning_preference_note: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _require_target(self) -> Self:
        if self.room_id is None and self.room_type is None:
            raise ValueError("either room_id or room_type is required")
        return self


class StaySummary(BaseModel):
    """One historical stay for the guest history view."""

    guest_id: str
    room_number: int
    floor: int
    checked_in_at: datetime
    checked_out_at: datetime | None
    nights: int
    total_minor_units: int | None = None  # null while still checked in
    bill_id: str | None = None


class GuestHistoryOut(BaseModel):
    """Loyalty aggregate keyed by phone — covers all past stays."""

    phone: str
    full_name: str
    stays: list[StaySummary]
    total_stays: int
    total_nights: int
    total_spent_minor_units: int
    last_checked_in_at: datetime | None
    repeat_visitor: bool


class DNDRequest(BaseModel):
    """Body for `PUT /guests/{id}/dnd`. Boolean wrapper kept explicit so the
    OpenAPI schema documents the toggle clearly."""

    do_not_disturb: bool


class CleaningPreferenceRequest(BaseModel):
    """Body for `PUT /guests/{id}/cleaning-preference`."""

    cleaning_preference: CleaningPreference
    cleaning_preference_note: str | None = Field(default=None, max_length=200)


class DailyCount(BaseModel):
    """One data point in the dashboard's "guests over time" chart."""

    date: date
    count: int


class GuestOut(BaseModel):
    """Guest projection for the dashboard. Excludes passport_number on
    purpose — that field is sensitive and only the detail endpoint returns it.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    phone: str
    room_id: str
    room_number: int
    floor: int
    room_type: RoomType
    checked_in_at: datetime
    checked_out_at: datetime | None = None
    expected_checkout_at: datetime
    nightly_rate_locked_minor_units: int
    do_not_disturb: bool = False
    cleaning_preference: CleaningPreference = CleaningPreference.AFTERNOON
    cleaning_preference_note: str | None = None
    auth_user_id: str | None = None


class CheckInResponse(GuestOut):
    """Extended response returned only from the check-in endpoint.
    Includes the plain-text PIN so reception can hand it to the guest."""

    guest_pin: str
    guest_login: str
