"""SQLAlchemy ORM models for the `maintenance` schema."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.config import settings

SCHEMA = settings.service_schema


class Base(DeclarativeBase):
    pass


class Issue(Base):
    """A reported maintenance problem.

    Issues live here for the lifetime of the system — even after they are
    resolved we keep them so the manager view can show history and the
    debugging story can reference real activity.

    `room_id`, `room_number` and `floor` are denormalised from reception
    because services don't reach across each other's schemas.
    """

    __tablename__ = "issues"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    room_number: Mapped[int] = mapped_column(Integer, nullable=False)
    floor: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    urgency: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="reported")
    reported_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    assigned_technician_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # Denormalised snapshot of the technician at the moment of assignment,
    # so the guest portal projection (in reception-service) and the manager
    # view can show "kim keladi + telefoni" without cross-service calls.
    assigned_technician_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    assigned_technician_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Technician(Base):
    """Local projection of staff users with role=technician (and any other
    role we may want to assign issues to in future), fed by `users.*`
    events from auth-service.

    Maintenance owns its own schema, so we can never join across to
    auth.users. The projection lets the assign endpoint snapshot the
    technician's name+phone onto the Issue without an HTTP call back.
    """

    __tablename__ = "technicians"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
