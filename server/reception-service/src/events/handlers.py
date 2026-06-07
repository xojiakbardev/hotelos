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

from sqlalchemy import select

from src.core.db import async_session_factory
from src.domain.enums import Cleanliness, RoomStatus
from src.domain.models import Guest, MaintenanceProjection
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

    Two side effects:
      * Flip the room's cleanliness to `maintenance` so the assignment
        algorithm excludes it from new check-ins until the issue is
        resolved. We don't touch `status` — if a guest was already in
        the room, the guest stays.
      * Insert the issue into the guest portal projection. We link it to
        whichever guest is currently checked into the room so the guest
        dashboard can show "your reported issue".
    """
    payload = envelope.get("payload") or {}
    raw_id = payload.get("room_id")
    issue_id = payload.get("issue_id")
    if not raw_id:
        return
    room_uuid = uuid.UUID(raw_id)
    async with async_session_factory() as session:
        async with session.begin():
            rooms = RoomRepository(session)
            room = await rooms.get(room_uuid)
            if room is not None and room.cleanliness_status != Cleanliness.MAINTENANCE.value:
                room.cleanliness_status = Cleanliness.MAINTENANCE.value

            if not issue_id:
                return
            # Find the current guest in the room (the issue's "owner" from
            # the portal's perspective). Might be None if reception
            # reported it for an empty room.
            stmt = select(Guest).where(
                Guest.room_id == room_uuid, Guest.checked_out_at.is_(None)
            )
            guest = (await session.execute(stmt)).scalars().first()
            existing = await session.get(MaintenanceProjection, uuid.UUID(issue_id))
            if existing is not None:
                return  # idempotent — duplicate delivery
            session.add(
                MaintenanceProjection(
                    id=uuid.UUID(issue_id),
                    guest_id=guest.id if guest else None,
                    room_id=room_uuid,
                    room_number=int(payload.get("room_number") or 0),
                    floor=int(payload.get("floor") or 0),
                    urgency=str(payload.get("urgency") or "normal"),
                    description=str(payload.get("description") or "")[:500],
                    status="reported",
                    reported_at=_parse_dt(payload.get("reported_at")),
                )
            )


async def on_maintenance_assigned(envelope: dict) -> None:
    """Maintenance assigned a technician. Update the projection so the
    guest portal can show who is coming + their phone number.
    """
    payload = envelope.get("payload") or {}
    issue_id = payload.get("issue_id")
    if not issue_id:
        return
    async with async_session_factory() as session:
        async with session.begin():
            row = await session.get(MaintenanceProjection, uuid.UUID(issue_id))
            if row is None:
                return
            row.status = "assigned"
            row.technician_name = payload.get("technician_name")
            row.technician_phone = payload.get("technician_phone")
            row.assigned_at = _parse_dt(payload.get("assigned_at"))


async def on_maintenance_resolved(envelope: dict) -> None:
    """Maintenance is done. The room is no longer flagged for maintenance,
    but it still needs a cleaning pass before reuse — we set cleanliness
    to `dirty`. Housekeeping subscribes to the same event in parallel and
    enqueues the room so the cleaner sees it on their queue page.

    Also closes out the guest portal projection.
    """
    payload = envelope.get("payload") or {}
    raw_id = payload.get("room_id")
    issue_id = payload.get("issue_id")
    if not raw_id:
        return
    async with async_session_factory() as session:
        async with session.begin():
            rooms = RoomRepository(session)
            room = await rooms.get(uuid.UUID(raw_id))
            if room is not None and room.cleanliness_status == Cleanliness.MAINTENANCE.value:
                room.cleanliness_status = Cleanliness.DIRTY.value

            if issue_id:
                row = await session.get(MaintenanceProjection, uuid.UUID(issue_id))
                if row is not None:
                    row.status = "resolved"
                    row.resolved_at = _parse_dt(payload.get("resolved_at"))
