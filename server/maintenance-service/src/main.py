"""FastAPI app for maintenance-service.

Maintenance only publishes events — it doesn't subscribe to anything, so
the lifespan is simpler than reception's or housekeeping's.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.exceptions import install_handlers
from src.api.routers import issues as issues_router
from src.core.broker import create_redis
from src.core.config import settings
from src.core.db import engine
from src.events.publisher import EventPublisher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
logger = logging.getLogger("maintenance-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = create_redis()
    app.state.publisher = EventPublisher(app.state.redis, publisher_name=settings.service_name)
    logger.info("maintenance-service ready (redis=%s)", settings.redis_url)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()


app = FastAPI(
    title="HotelOS — maintenance-service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)
install_handlers(app)
app.include_router(issues_router.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}
