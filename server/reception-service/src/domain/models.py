"""SQLAlchemy ORM models for the `reception` schema.

Reception owns the canonical inventory of rooms and the canonical record of
guests. Other services see this state only through broker events.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.core.config import settings

SCHEMA = settings.service_schema


class Base(DeclarativeBase):
    pass


class Room(Base):
    """A physical room. Inventory list — implements the brief's required
    "array/list" data structure (the table is the list)."""

    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("room_number", name="uq_rooms_room_number"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_number: Mapped[int] = mapped_column(Integer, nullable=False)
    floor: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    room_type: Mapped[str] = mapped_column(String(16), nullable=False)
    proximity: Mapped[str] = mapped_column(String(16), nullable=False)
    cleanliness_status: Mapped[str] = mapped_column(String(16), nullable=False, default="clean")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="available")
    # Prices stored as minor units (tiyin / cents) to avoid floating-point money.
    nightly_rate_minor_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Drives the "longest clean wins" tiebreaker in the assignment algorithm.
    last_cleaned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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

    guests: Mapped[list["Guest"]] = relationship(back_populates="room")


class Guest(Base):
    """A guest. Active guests are those with `checked_out_at IS NULL`.

    Conceptually fulfils the brief's required "dictionary/map" structure — the
    table is the canonical map from guest_id → guest record.
    """

    __tablename__ = "guests"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    passport_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.rooms.id"),
        nullable=False,
        index=True,
    )
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    checked_out_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expected_checkout_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Locked at check-in so a later rate change can't retroactively alter
    # the bill. Computed billing reads this column, not the room's current rate.
    nightly_rate_locked_minor_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Cleaner-facing "do not disturb" toggle. The cleaning queue surfaces this
    # so staff knock politely / skip the room as configured.
    do_not_disturb: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    # When the guest prefers cleaning to happen. Free-text note paired with
    # the enum lets reception capture a "10:30 sharp" style request when the
    # caller chose CUSTOM.
    cleaning_preference: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="afternoon", default="afternoon"
    )
    cleaning_preference_note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    room: Mapped[Room] = relationship(back_populates="guests")
    bills: Mapped[list["Bill"]] = relationship(back_populates="guest")


class Bill(Base):
    """Final bill produced at check-out by the billing algorithm.

    Money is stored in minor units (e.g. tiyin) as a bigint — never floats.
    The four `*_minor_units` columns hold the breakdown so the dashboard can
    show "what was this charge for?" without us having to keep a separate
    `bill_lines` table at this milestone (we'll add lines when room-service
    orders land).
    """

    __tablename__ = "bills"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.guests.id"),
        nullable=False,
        index=True,
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.rooms.id"),
        nullable=False,
    )
    nights: Mapped[int] = mapped_column(Integer, nullable=False)
    nightly_rate_minor_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    room_cost_minor_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    room_service_charges_minor_units: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    extras_minor_units: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    discount_minor_units: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_minor_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    finalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    guest: Mapped[Guest] = relationship(back_populates="bills")


class Order(Base):
    """Room-service order. Reception owns the lifecycle; room-service
    receives event-driven mirrors for the kitchen view.

    Line items live as JSONB on the row instead of a separate table —
    orders are append-only (no edits after submit) and the bill query
    aggregates by total, not by line, so a row-per-item is overkill.

    Schema for `items`:
        [
          {"name": "Espresso", "qty": 2, "price_minor_units": 350},
          {"name": "Club sandwich", "qty": 1, "price_minor_units": 1200}
        ]
    """

    __tablename__ = "orders"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.guests.id"),
        nullable=False,
        index=True,
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.rooms.id"),
        nullable=False,
    )
    room_number: Mapped[int] = mapped_column(Integer, nullable=False)
    floor: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="received")
    items: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    total_minor_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    taken_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # Flipped to True the moment the guest's bill includes this order.
    # The check-out billing query filters on `is_billed=False` so a retried
    # check-out can never double-charge an already-billed order.
    is_billed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    billed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    preparing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivering_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
