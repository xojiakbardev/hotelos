"""Channel names housekeeping publishes or subscribes to."""

from __future__ import annotations


class Channels:
    # Housekeeping publishes these:
    ROOM_ADDED_TO_CLEANING_QUEUE = "rooms.added_to_cleaning_queue"
    ROOM_CLEANING_STARTED = "rooms.cleaning_started"
    ROOM_CLEANED = "rooms.cleaned"

    # Housekeeping subscribes to these:
    ROOM_VACATED = "rooms.vacated"
    MAINTENANCE_RESOLVED = "maintenance.resolved"
