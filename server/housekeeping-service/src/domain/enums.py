"""Housekeeping enums."""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    MANAGER = "manager"
    RECEPTION = "reception"
    TECHNICIAN = "technician"
    CLEANER = "cleaner"
    GUEST = "guest"


class CleaningStatus(str, Enum):
    """Cleaning queue entry lifecycle.

      pending     → just added, no cleaner has started yet (the FIFO head
                    of the queue is the next room to be picked up).
      in_progress → a cleaner has claimed the entry and is working on it.
      completed   → cleaner marked it done; the room.cleaned event has been
                    published.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
