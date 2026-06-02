"""FastAPI app for housekeeping-service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.exceptions import install_handlers
from src.api.routers import queue as queue_router
from src.core.broker import create_redis
from src.core.config import settings
from src.core.db import engine
from src.events.handlers import make_on_room_vacated
from src.events.publisher import EventPublisher
from src.events.subscriber import EventSubscriber
from src.events.topics import Channels

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
logger = logging.getLogger("housekeeping-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = create_redis()
    app.state.publisher = EventPublisher(app.state.redis, publisher_name=settings.service_name)

    subscriber = EventSubscriber(app.state.redis)
    # The same enqueue handler serves both events — the brief calls for
    # rooms to be re-cleaned after both a guest check-out AND a completed
    # maintenance job.
    enqueue = make_on_room_vacated(app.state.publisher)
    subscriber.on(Channels.ROOM_VACATED, enqueue)
    subscriber.on(Channels.MAINTENANCE_RESOLVED, enqueue)
    await subscriber.start()
    app.state.subscriber = subscriber

    logger.info("housekeeping-service ready (redis=%s)", settings.redis_url)
    try:
        yield
    finally:
        await app.state.subscriber.stop()
        await app.state.redis.aclose()
        await engine.dispose()


app = FastAPI(
    title="HotelOS — housekeeping-service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)
install_handlers(app)
app.include_router(queue_router.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
