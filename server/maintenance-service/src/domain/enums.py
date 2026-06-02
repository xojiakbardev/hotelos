"""Maintenance enums."""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    MANAGER = "manager"
    RECEPTION = "reception"
    TECHNICIAN = "technician"
    CLEANER = "cleaner"


class Urgency(str, Enum):
    """Reported urgency drives the priority queue ordering. Lower numeric
    rank (see `services/priority_queue.py::URGENCY_RANK`) means higher
    priority — Critical wins."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class IssueStatus(str, Enum):
    """Issue lifecycle.

      reported  → just created, not yet claimed by a technician.
      assigned  → a technician has taken responsibility for it.
      resolved  → fix applied; the room is no longer flagged for
                  maintenance (but reception will still want it cleaned
                  before re-rental).
    """

    REPORTED = "reported"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
