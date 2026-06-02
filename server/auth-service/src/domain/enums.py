"""Enumerations shared across the auth-service. Persisted as their .value string."""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    MANAGER = "manager"
    RECEPTION = "reception"
    TECHNICIAN = "technician"
    CLEANER = "cleaner"

    @classmethod
    def list(cls) -> list[str]:
        return [r.value for r in cls]
