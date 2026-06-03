"""Channel names housekeeping publishes or subscribes to."""

from __future__ import annotations


class Channels:
    # Housekeeping publishes these:
    ROOM_ADDED_TO_CLEANING_QUEUE = "rooms.added_to_cleaning_queue"
    ROOM_CLEANING_STARTED = "rooms.cleaning_started"
    ROOM_CLEANED = "rooms.cleaned"
    # Re-broadcast of guest DND / preference changes so the cleaner UI can
    # patch its queue card without an extra HTTP refetch. Cleaner role
    # already subscribes to `housekeeping.*` patterns.
    HOUSEKEEPING_ENTRY_UPDATED = "housekeeping.entry_updated"

    # Housekeeping subscribes to these:
    ROOM_VACATED = "rooms.vacated"
    MAINTENANCE_RESOLVED = "maintenance.resolved"
    GUEST_DND_CHANGED = "guests.dnd_changed"
    GUEST_PREFERENCES_CHANGED = "guests.preferences_changed"
