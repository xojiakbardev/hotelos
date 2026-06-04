"""Inbound event handlers for reception-service.

Each handler runs inside its own DB session (subscribers live outside the
FastAPI request scope, so we can't use Depends here). Handlers are
idempotent by checking current state before applying changes — Redis
Pub/Sub is at-most-once, but we still defend against duplicate delivery
via misconfiguration or replay.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from src.core.db import async_session_factory
from src.domain.enums import Cleanliness, RoomStatus
from src.infra.repositories.room_repository import RoomRepository

logger = logging.getLogger("reception-service.handlers")


def _parse_dt(value: str | None) -> datetime:
    """Tolerant ISO-8601 parser. Falls back to "now" so a malformed event
    still moves the state machine forward instead of stalling it."""
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


async def on_room_cleaning_started(envelope: dict) -> None:
    """Housekeeping told us a cleaner started cleaning a room.

    We update reception's room copy so the dashboard's cleanliness column
    matches reality. The room stays `status=available` (no guest) but is
    no longer assignable because cleanliness != clean.
    """
    payload = envelope.get("payload") or {}
    raw_id = payload.get("room_id")
    if not raw_id:
        return
    async with async_session_factory() as session:
        async with session.begin():
            rooms = RoomRepository(session)
            room = await rooms.get(uuid.UUID(raw_id))
            if room is None or room.cleanliness_status == Cleanliness.CLEANING.value:
                return
            room.cleanliness_status = Cleanliness.CLEANING.value


async def on_room_cleaned(envelope: dict) -> None:
    """Housekeeping told us a room is clean and ready to be reassigned.

    This closes the lifecycle loop:
      occupied → vacated → dirty → cleaning → **clean (here)** → assignable again.
    Also recalculates freshness_score and dynamic_price.
    """
    from src.services.freshness import compute_dynamic_price

    payload = envelope.get("payload") or {}
    raw_id = payload.get("room_id")
    if not raw_id:
        return
    cleaned_at = _parse_dt(payload.get("cleaned_at"))
    async with async_session_factory() as session:
        async with session.begin():
            rooms = RoomRepository(session)
            room = await rooms.get(uuid.UUID(raw_id))
            if room is None:
                return
            if (
                room.cleanliness_status == Cleanliness.CLEAN.value
                and room.status == RoomStatus.AVAILABLE.value
            ):
                logger.debug("room %s already clean+available, skipping", raw_id)
                return
            room.cleanliness_status = Cleanliness.CLEAN.value
            room.status = RoomStatus.AVAILABLE.value
            room.last_cleaned_at = cleaned_at
            room.freshness_score = 1.0
            room.dynamic_price_minor_units = compute_dynamic_price(
                room.nightly_rate_minor_units, 1.0
            )


async def on_maintenance_reported(envelope: dict) -> None:
    """A technical issue was reported against a room.

    Flip the room's cleanliness to `maintenance` so the assignment
    algorithm excludes it from new check-ins until the issue is resolved.
    We don't touch `status` — if a guest was already in the room, the
    guest stays.
    """
    payload = envelope.get("payload") or {}
    raw_id = payload.get("room_id")
    if not raw_id:
        return
    async with async_session_factory() as session:
        async with session.begin():
            rooms = RoomRepository(session)
            room = await rooms.get(uuid.UUID(raw_id))
            if room is None or room.cleanliness_status == Cleanliness.MAINTENANCE.value:
                return
            room.cleanliness_status = Cleanliness.MAINTENANCE.value


async def on_maintenance_resolved(envelope: dict) -> None:
    """Maintenance is done. The room is no longer flagged for maintenance,
    but it still needs a cleaning pass before reuse — we set cleanliness
    to `dirty`. Housekeeping subscribes to the same event in parallel and
    enqueues the room so the cleaner sees it on their queue page.
    """
    payload = envelope.get("payload") or {}
    raw_id = payload.get("room_id")
    if not raw_id:
        return
    async with async_session_factory() as session:
        async with session.begin():
            rooms = RoomRepository(session)
            room = await rooms.get(uuid.UUID(raw_id))
            if room is None:
                return
            if room.cleanliness_status == Cleanliness.MAINTENANCE.value:
                room.cleanliness_status = Cleanliness.DIRTY.value
