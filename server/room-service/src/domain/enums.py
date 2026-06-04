"""Room-service enums."""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    MANAGER = "manager"
    RECEPTION = "reception"
    TECHNICIAN = "technician"
    CLEANER = "cleaner"
    GUEST = "guest"


class OrderStatus(str, Enum):
    """Lifecycle copied from reception. Room-service is a *projection* —
    we don't enforce transitions here, we just record what reception tells us.
    """

    RECEIVED = "received"
    PREPARING = "preparing"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
