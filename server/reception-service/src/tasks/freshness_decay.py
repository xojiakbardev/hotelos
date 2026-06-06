"""Background task: periodically decay freshness and mark stale rooms as dirty.

Runs every 5 minutes. For each room that is currently `clean` + `available`:
  1. Recompute freshness_score from last_cleaned_at
  2. Recompute dynamic_price
  3. If freshness_score hits 0.0, flip cleanliness_status to `dirty`

This ensures rooms don't stay "clean" forever — after FRESHNESS_DECAY_HOURS
(24h by default), the room automatically needs re-cleaning.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from src.core.db import async_session_factory
from src.domain.enums import Cleanliness, RoomStatus
from src.domain.models import Room
from src.services.freshness import (
    FRESHNESS_DECAY_HOURS,
    compute_dynamic_price,
    compute_freshness_score,
)

logger = logging.getLogger("reception-service.freshness-decay")

# How often to run the decay check (seconds)
DECAY_INTERVAL_SECONDS: int = 5 * 60  # every 5 minutes


async def freshness_decay_loop() -> None:
    """Infinite loop that periodically updates freshness for all clean rooms."""
    logger.info(
        "freshness decay task started (interval=%ds, full_decay=%dh)",
        DECAY_INTERVAL_SECONDS,
        int(FRESHNESS_DECAY_HOURS),
    )
    while True:
        try:
            await _tick()
        except asyncio.CancelledError:
            logger.info("freshness decay task cancelled")
            return
        except Exception:
            logger.exception("freshness decay tick failed")
        await asyncio.sleep(DECAY_INTERVAL_SECONDS)


async def _tick() -> None:
    """Single pass: update all clean+available rooms."""
    async with async_session_factory() as session:
        async with session.begin():
            stmt = select(Room).where(
                Room.cleanliness_status == Cleanliness.CLEAN.value,
                Room.status == RoomStatus.AVAILABLE.value,
            )
            rooms = list((await session.execute(stmt)).scalars().all())

            dirty_rooms: list[Room] = []
            for room in rooms:
                new_score = compute_freshness_score(room.last_cleaned_at)
                room.freshness_score = new_score
                room.dynamic_price_minor_units = compute_dynamic_price(
                    room.nightly_rate_minor_units, new_score
                )
                # If freshness reached zero, room needs re-cleaning
                if new_score <= 0.0:
                    room.cleanliness_status = Cleanliness.DIRTY.value
                    dirty_rooms.append(room)

            if dirty_rooms:
                logger.info(
                    "freshness decay: %d room(s) marked dirty (stale after %dh)",
                    len(dirty_rooms),
                    int(FRESHNESS_DECAY_HOURS),
                )

    # Publish cleaning_requested events outside the DB transaction
    if dirty_rooms:
        from src.core.broker import create_redis
        from src.events.publisher import EventPublisher
        from src.events.topics import Channels

        redis = create_redis()
        publisher = EventPublisher(redis, publisher_name="reception-service")
        try:
            for room in dirty_rooms:
                await publisher.publish(
                    channel=Channels.ROOM_CLEANING_REQUESTED,
                    payload={
                        "room_id": str(room.id),
                        "room_number": room.room_number,
                        "floor": room.floor,
                        "reason": "freshness_decay",
                    },
                )
        finally:
            await redis.aclose()
