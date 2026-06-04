"""FastAPI app for reception-service.

Lifespan responsibilities:
  * open the Redis broker connection,
  * register the EventPublisher used by the routers,
  * wire up the inbound subscriber and start its background task.

All four close cleanly on shutdown.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.exceptions import install_handlers
from src.api.routers import guests as guests_router
from src.api.routers import guest_portal as guest_portal_router
from src.api.routers import metrics as metrics_router
from src.api.routers import orders as orders_router
from src.api.routers import reservations as reservations_router
from src.api.routers import rooms as rooms_router
from src.core.broker import create_redis
from src.core.config import settings
from src.core.db import engine
from src.events.handlers import (
    on_maintenance_reported,
    on_maintenance_resolved,
    on_room_cleaned,
    on_room_cleaning_started,
)
from src.events.publisher import EventPublisher
from src.events.subscriber import EventSubscriber
from src.events.topics import Channels

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
logger = logging.getLogger("reception-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = create_redis()
    app.state.publisher = EventPublisher(app.state.redis, publisher_name=settings.service_name)

    subscriber = EventSubscriber(app.state.redis)
    subscriber.on(Channels.ROOM_CLEANING_STARTED, on_room_cleaning_started)
    subscriber.on(Channels.ROOM_CLEANED, on_room_cleaned)
    subscriber.on(Channels.MAINTENANCE_REPORTED, on_maintenance_reported)
    subscriber.on(Channels.MAINTENANCE_RESOLVED, on_maintenance_resolved)
    await subscriber.start()
    app.state.subscriber = subscriber

    # Background task: decay freshness and auto-dirty stale rooms
    import asyncio
    from src.tasks.freshness_decay import freshness_decay_loop
    decay_task = asyncio.create_task(freshness_decay_loop(), name="freshness-decay")
    app.state.decay_task = decay_task

    logger.info("reception-service ready (redis=%s)", settings.redis_url)
    try:
        yield
    finally:
        decay_task.cancel()
        try:
            await decay_task
        except asyncio.CancelledError:
            pass
        await app.state.subscriber.stop()
        await app.state.redis.aclose()
        await engine.dispose()


app = FastAPI(
    title="HotelOS — reception-service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)
install_handlers(app)
app.include_router(rooms_router.router)
app.include_router(guests_router.router)
app.include_router(orders_router.router)
app.include_router(reservations_router.router)
app.include_router(metrics_router.router)
app.include_router(guest_portal_router.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
