"""Schemas for the maintenance API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import IssueStatus, Urgency


class IssueReport(BaseModel):
    """What reception / manager submits when reporting a problem."""

    room_id: uuid.UUID
    room_number: int = Field(..., ge=1, le=9999)
    floor: int = Field(..., ge=1, le=99)
    urgency: Urgency
    description: str = Field(..., min_length=3, max_length=500)


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    room_id: uuid.UUID
    room_number: int
    floor: int
    urgency: Urgency
    description: str
    status: IssueStatus
    reported_by_user_id: uuid.UUID
    reported_at: datetime
    assigned_technician_id: uuid.UUID | None = None
    assigned_technician_name: str | None = None
    assigned_technician_phone: str | None = None
    assigned_at: datetime | None = None
    resolved_at: datetime | None = None
    resolved_by_user_id: uuid.UUID | None = None
