"""SQLAlchemy ORM models for the `reception` schema.

Reception owns the canonical inventory of rooms and the canonical record of
guests. Other services see this state only through broker events.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
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
    # Freshness score (0.0–1.0) — decays over time since last cleaning.
    freshness_score: Mapped[float] = mapped_column(
        nullable=False, server_default="1.0", default=1.0
    )
    # Dynamic price adjusted by freshness. Updated when room is cleaned.
    dynamic_price_minor_units: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0", default=0
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
    # Logical reference to auth.users.id — no FK because cross-schema is forbidden.
    auth_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
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


class Reservation(Base):
    """A future booking. Sits between "guest exists somewhere out there" and
    "guest physically walked through the door".

    Active reservations (PENDING + CONFIRMED) block the room for their date
    range. Two concurrent reservation creates that target the same room with
    overlapping dates serialise on the room row's FOR UPDATE lock — see
    `services/reservation_assignment.py`.

    Once checked in we create a Guest row and link `guest_id` so the bill
    flow stays unified with walk-ins.
    """

    __tablename__ = "reservations"
    __table_args__ = (
        Index("ix_reservations_room_dates", "room_id", "check_in_date", "check_out_date"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Guest contact info — captured at reservation time. A Guest row gets
    # created later, at check-in, so we can fall back to walk-in lookups.
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    passport_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.rooms.id"),
        nullable=False,
        index=True,
    )
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    # Locked at reservation time so a later rate change doesn't surprise
    # the guest at check-in.
    nightly_rate_locked_minor_units: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Set when status flips to CHECKED_IN.
    guest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.guests.id"),
        nullable=True,
    )
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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

    room: Mapped[Room] = relationship()


class CleaningRequest(Base):
    """Guest-initiated cleaning request. Tracked separately from the
    housekeeping queue (which is triggered by room.vacated events).
    Guests create these from their self-service portal."""

    __tablename__ = "cleaning_requests"
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
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    preferred_time: Mapped[str] = mapped_column(String(16), nullable=False, default="afternoon")
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MaintenanceProjection(Base):
    """Local read-model of maintenance issues owned by maintenance-service.

    Built from `maintenance.*` events. Lets the guest portal show the
    status of issues a guest reported (including the assigned technician's
    name + phone, denormalised on the event) without reception-service
    ever having to call into maintenance-service over HTTP.

    `id` mirrors maintenance.issues.id. We carry `guest_id` (nullable —
    issues reported by staff for an unoccupied room won't have one) so
    the dashboard query is a simple `where guest_id = :id`.
    """

    __tablename__ = "maintenance_projection"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    guest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    room_number: Mapped[int] = mapped_column(Integer, nullable=False)
    floor: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    urgency: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="reported")
    technician_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    technician_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
