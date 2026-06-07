"""FastAPI app factory for auth-service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.exceptions import install_handlers
from src.api.routers import auth as auth_router
from src.api.routers import users as users_router
from src.core.broker import create_redis
from src.core.config import settings
from src.core.db import engine
from src.events.handlers import (
    on_guest_credential_created,
    on_guest_credential_deactivated,
    on_guest_credential_updated,
)
from src.events.publisher import EventPublisher
from src.events.subscriber import EventSubscriber
from src.events.topics import Channels

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")
logger = logging.getLogger("auth-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = create_redis()
    app.state.publisher = EventPublisher(app.state.redis, publisher_name=settings.service_name)

    # Replay current technician roster so subscribers can rebuild a stale
    # projection cache after a restart without us hand-rolling a migration.
    try:
        from src.core.db import async_session_factory
        from src.domain.enums import UserRole
        from src.infra.repositories.user_repository import UserRepository

        async with async_session_factory() as session:
            users = await UserRepository(session).list_active()
            for u in users:
                if u.role in (UserRole.TECHNICIAN, UserRole.MANAGER, UserRole.RECEPTION, UserRole.CLEANER, UserRole.KITCHEN):
                    await app.state.publisher.publish(
                        channel=Channels.USER_CREATED,
                        payload={
                            "user_id": str(u.id),
                            "phone": u.phone,
                            "full_name": u.full_name,
                            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
                            "is_active": u.is_active,
                        },
                    )
    except Exception:
        logger.exception("startup user replay failed (non-fatal)")

    subscriber = EventSubscriber(app.state.redis)
    subscriber.on(Channels.GUEST_CREDENTIAL_CREATED, on_guest_credential_created)
    subscriber.on(Channels.GUEST_CREDENTIAL_DEACTIVATED, on_guest_credential_deactivated)
    subscriber.on(Channels.GUEST_CREDENTIAL_UPDATED, on_guest_credential_updated)
    await subscriber.start()
    app.state.subscriber = subscriber

    logger.info("auth-service ready (redis=%s)", settings.redis_url)
    try:
        yield
    finally:
        await app.state.subscriber.stop()
        await app.state.redis.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title="HotelOS — auth-service",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    install_handlers(application)
    application.include_router(auth_router.router)
    application.include_router(users_router.router)

    from src.api.routers import audit as audit_router
    application.include_router(audit_router.router)

    @application.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    return application


app = create_app()
