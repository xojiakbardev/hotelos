"""Enumerations shared across the auth-service. Persisted as their .value string."""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    MANAGER = "manager"
    RECEPTION = "reception"
    TECHNICIAN = "technician"
    CLEANER = "cleaner"
    KITCHEN = "kitchen"
    GUEST = "guest"

    @classmethod
    def staff_roles(cls) -> list["UserRole"]:
        """Roles that are hotel staff (excludes guest)."""
        return [cls.MANAGER, cls.RECEPTION, cls.TECHNICIAN, cls.CLEANER, cls.KITCHEN]

    @classmethod
    def list(cls) -> list[str]:
        return [r.value for r in cls]
