"""Schemas for the cleaning queue API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.domain.enums import CleaningStatus


class CleaningEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    room_id: uuid.UUID
    room_number: int
    floor: int
    status: CleaningStatus
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    assigned_cleaner_id: uuid.UUID | None = None
