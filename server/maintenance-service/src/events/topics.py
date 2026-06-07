"""Maintenance channel names."""

from __future__ import annotations


class Channels:
    # Maintenance publishes these:
    MAINTENANCE_REPORTED = "maintenance.reported"
    MAINTENANCE_ASSIGNED = "maintenance.assigned"
    MAINTENANCE_RESOLVED = "maintenance.resolved"

    # Maintenance subscribes to these (published by auth-service):
    USER_CREATED = "users.created"
    USER_UPDATED = "users.updated"
    USER_DEACTIVATED = "users.deactivated"

    # Reception publishes this when a guest reports an issue from the
    # portal. Maintenance materialises it into a real Issue row and then
    # publishes the canonical MAINTENANCE_REPORTED event.
    GUEST_PORTAL_MAINTENANCE_REQUESTED = "guest_portal.maintenance_requested"
