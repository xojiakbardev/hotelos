"""Channel + event names that reception publishes or subscribes to.

The same string is used both as the Redis channel name and as the `event`
field inside the envelope — see `docs/events.md`. ws-gateway pattern-matches
channels (e.g. `rooms.*`) to decide which connected clients receive what,
so prefixes matter.
"""

from __future__ import annotations


class Channels:
    # Reception publishes these:
    GUEST_CHECKED_IN = "guests.checked_in"
    GUEST_CHECKED_OUT = "guests.checked_out"
    GUEST_DND_CHANGED = "guests.dnd_changed"
    GUEST_PREFERENCES_CHANGED = "guests.preferences_changed"
    GUEST_UPDATED = "guests.updated"
    GUEST_CREDENTIAL_CREATED = "guests.credential_created"
    GUEST_CREDENTIAL_DEACTIVATED = "guests.credential_deactivated"
    GUEST_CREDENTIAL_UPDATED = "guests.credential_updated"
    RESERVATION_CREATED = "reservations.created"
    RESERVATION_CONFIRMED = "reservations.confirmed"
    RESERVATION_CANCELLED = "reservations.cancelled"
    RESERVATION_NO_SHOW = "reservations.no_show"
    ROOM_VACATED = "rooms.vacated"
    ROOM_CLEANING_REQUESTED = "rooms.cleaning_requested"
    BILL_FINALIZED = "bills.finalized"
    ORDER_RECEIVED = "orders.received"
    ORDER_PREPARING = "orders.preparing"
    ORDER_DELIVERING = "orders.delivering"
    ORDER_DELIVERED = "orders.delivered"

    # Reception subscribes to these:
    ROOM_CLEANING_STARTED = "rooms.cleaning_started"
    ROOM_CLEANED = "rooms.cleaned"
    MAINTENANCE_REPORTED = "maintenance.reported"
    MAINTENANCE_ASSIGNED = "maintenance.assigned"
    MAINTENANCE_RESOLVED = "maintenance.resolved"

    # Reception publishes this when a guest reports an issue from the
    # portal. maintenance-service subscribes, creates a real Issue row,
    # and emits the canonical MAINTENANCE_REPORTED event itself.
    GUEST_PORTAL_MAINTENANCE_REQUESTED = "guest_portal.maintenance_requested"
