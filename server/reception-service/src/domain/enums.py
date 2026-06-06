"""Enums used across the reception service.

All enums inherit `(str, Enum)` so instances behave as strings at the DB layer
— asyncpg writes the `.value` directly and SQLAlchemy doesn't need a custom
type adapter.
"""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    """Mirrors the role enum in auth-service. Duplicated intentionally — each
    microservice owns its own copy so a future rename in auth-service can't
    silently break this one."""

    MANAGER = "manager"
    RECEPTION = "reception"
    TECHNICIAN = "technician"
    CLEANER = "cleaner"
    KITCHEN = "kitchen"
    GUEST = "guest"


class RoomType(str, Enum):
    SINGLE = "single"
    DOUBLE = "double"
    SUITE = "suite"
    ACCESSIBLE = "accessible"


class Proximity(str, Enum):
    """Which vertical-circulation feature the room is closest to."""

    ELEVATOR = "elevator"
    STAIRS = "stairs"
    OTHER = "other"


class Cleanliness(str, Enum):
    CLEAN = "clean"
    DIRTY = "dirty"
    CLEANING = "cleaning"
    MAINTENANCE = "maintenance"


class RoomStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    OUT_OF_SERVICE = "out_of_service"


class CleaningPreference(str, Enum):
    """When the guest prefers to be cleaned (set at check-in, updatable mid-stay).

    `CUSTOM` means the receptionist agreed a specific window with the guest
    and recorded it as a free-text note alongside; the enum tells housekeeping
    "ask reception before knocking".
    """

    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    CUSTOM = "custom"


class ReservationStatus(str, Enum):
    """Future booking lifecycle.

    A reservation begins PENDING (tentative). It can be:
      * CONFIRMED — booking accepted, room is now blocked for the date range.
      * CHECKED_IN — guest arrived; we create a Guest row and set this status.
      * CANCELLED — voluntarily cancelled by the guest or reception.
      * NO_SHOW — date passed without check-in.

    The progression is one-way; once cancelled, no_show or checked_in, the
    reservation is terminal and cannot be reopened.
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


# Reservations that still hold the room (block overlapping dates).
ACTIVE_RESERVATION_STATUSES: frozenset[str] = frozenset(
    {ReservationStatus.PENDING.value, ReservationStatus.CONFIRMED.value}
)


class OrderStatus(str, Enum):
    """Room-service order lifecycle.

    Linear progression — no skipping, no going back. The `advance()` API
    moves an order to the *next* value in this order.
    """

    RECEIVED = "received"
    PREPARING = "preparing"
    DELIVERING = "delivering"
    DELIVERED = "delivered"


# Lookup used by `services/order_lifecycle.py::next_status`.
ORDER_LIFECYCLE: dict[OrderStatus, OrderStatus | None] = {
    OrderStatus.RECEIVED: OrderStatus.PREPARING,
    OrderStatus.PREPARING: OrderStatus.DELIVERING,
    OrderStatus.DELIVERING: OrderStatus.DELIVERED,
    OrderStatus.DELIVERED: None,  # terminal state
}
