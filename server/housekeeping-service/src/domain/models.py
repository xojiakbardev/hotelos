"""SQLAlchemy ORM models for the `housekeeping` schema.

The single table here is the cleaning queue — the brief's required "queue"
data structure. Rows ordered by `queued_at ASC` form a FIFO of rooms that
need attention. Cleaners pull the head of the queue (or any specific row
they want to claim) via the `start` endpoint.

Room data is denormalised from reception (we copy `room_number` and `floor`
at enqueue time) because services don't reach across each other's schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.config import settings

SCHEMA = settings.service_schema


class Base(DeclarativeBase):
    pass


class CleaningQueueEntry(Base):
    """A request to clean a specific room. One row per visit to the queue."""

    __tablename__ = "cleaning_queue_entries"
    __table_args__ = (
        # Prevent duplicate active queue entries for the same room — if a
        # `rooms.vacated` event is replayed, we no-op instead of double-queue.
        UniqueConstraint(
            "room_id",
            "status",
            name="uq_cleaning_queue_room_active",
        ),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Reception's UUID — we don't enforce an FK because the row lives in
    # another schema owned by another service.
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    room_number: Mapped[int] = mapped_column(Integer, nullable=False)
    floor: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_cleaner_id: Mapped[uuid.UUID | None] = mapped_column(
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
