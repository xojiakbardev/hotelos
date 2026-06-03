"""Inbound event handlers for housekeeping-service."""

from __future__ import annotations

import logging
import uuid

from src.core.broker import create_redis
from src.core.db import async_session_factory
from src.events.publisher import EventPublisher
from src.events.topics import Channels
from src.infra.repositories.cleaning_queue_repository import CleaningQueueRepository

logger = logging.getLogger("housekeeping-service.handlers")


def make_on_room_vacated(publisher: EventPublisher):
    """Factory binds the publisher closure so the subscriber loop doesn't
    have to look it up per message."""

    async def on_room_vacated(envelope: dict) -> None:
        payload = envelope.get("payload") or {}
        raw_id = payload.get("room_id")
        if not raw_id:
            return
        room_id = uuid.UUID(raw_id)
        room_number = int(payload.get("room_number", 0))
        floor = int(payload.get("floor", 0))

        async with async_session_factory() as session:
            async with session.begin():
                repo = CleaningQueueRepository(session)
                # Idempotency — if a queue entry for this room is already
                # open (pending or in_progress), the event is a replay; skip.
                if await repo.find_active_for_room(room_id) is not None:
                    logger.info("room %s already in queue, skipping replay", room_id)
                    return
                entry = await repo.enqueue(
                    room_id=room_id, room_number=room_number, floor=floor
                )
                snapshot = (str(entry.id), entry.queued_at.isoformat())

        await publisher.publish(
            channel=Channels.ROOM_ADDED_TO_CLEANING_QUEUE,
            payload={
                "entry_id": snapshot[0],
                "room_id": str(room_id),
                "room_number": room_number,
                "floor": floor,
                "queued_at": snapshot[1],
            },
        )

    return on_room_vacated


def make_on_guest_dnd_changed(publisher: EventPublisher):
    async def on_guest_dnd_changed(envelope: dict) -> None:
        """Mirror DND onto any active queue entry, then re-broadcast under
        `housekeeping.*` so the cleaner UI patches its card live."""
        payload = envelope.get("payload") or {}
        raw_id = payload.get("room_id")
        if not raw_id:
            return
        value = bool(payload.get("do_not_disturb", False))
        room_id = uuid.UUID(raw_id)
        async with async_session_factory() as session:
            async with session.begin():
                repo = CleaningQueueRepository(session)
                updated = await repo.set_dnd_for_room(room_id, value)
        if updated:
            await publisher.publish(
                channel=Channels.HOUSEKEEPING_ENTRY_UPDATED,
                payload={
                    "room_id": str(room_id),
                    "room_number": payload.get("room_number"),
                    "do_not_disturb": value,
                },
            )

    return on_guest_dnd_changed


def make_on_guest_preferences_changed(publisher: EventPublisher):
    async def on_guest_preferences_changed(envelope: dict) -> None:
        payload = envelope.get("payload") or {}
        raw_id = payload.get("room_id")
        if not raw_id:
            return
        preference = str(payload.get("cleaning_preference") or "afternoon")
        note = payload.get("cleaning_preference_note")
        room_id = uuid.UUID(raw_id)
        async with async_session_factory() as session:
            async with session.begin():
                repo = CleaningQueueRepository(session)
                updated = await repo.set_preference_for_room(
                    room_id, preference=preference, note=note
                )
        if updated:
            await publisher.publish(
                channel=Channels.HOUSEKEEPING_ENTRY_UPDATED,
                payload={
                    "room_id": str(room_id),
                    "room_number": payload.get("room_number"),
                    "cleaning_preference": preference,
                    "cleaning_preference_note": note,
                },
            )

    return on_guest_preferences_changed
