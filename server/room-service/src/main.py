"""FastAPI app for room-service.

This is the kitchen-side projection of reception's order lifecycle.
The lifespan subscribes to every order event reception publishes and
keeps the local `orders_mirror` table in sync.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.exceptions import install_handlers
from src.api.routers import orders as orders_router
from src.core.broker import create_redis
from src.core.config import settings
from src.core.db import engine
from src.domain.enums import OrderStatus
from src.events.handlers import make_on_advance, on_order_received
from src.events.publisher import EventPublisher
from src.events.subscriber import EventSubscriber
from src.events.topics import Channels

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
logger = logging.getLogger("room-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = create_redis()
    app.state.publisher = EventPublisher(app.state.redis, publisher_name=settings.service_name)

    subscriber = EventSubscriber(app.state.redis)
    subscriber.on(Channels.ORDER_RECEIVED, on_order_received)
    subscriber.on(Channels.ORDER_PREPARING, make_on_advance(OrderStatus.PREPARING))
    subscriber.on(Channels.ORDER_DELIVERING, make_on_advance(OrderStatus.DELIVERING))
    subscriber.on(Channels.ORDER_DELIVERED, make_on_advance(OrderStatus.DELIVERED))
    await subscriber.start()
    app.state.subscriber = subscriber

    logger.info("room-service ready (redis=%s)", settings.redis_url)
    try:
        yield
    finally:
        await app.state.subscriber.stop()
        await app.state.redis.aclose()
        await engine.dispose()


app = FastAPI(
    title="HotelOS — room-service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)
install_handlers(app)
app.include_router(orders_router.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
