"""FastAPI app factory for auth-service."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from src.api.exceptions import install_handlers
from src.api.routers import auth as auth_router
from src.api.routers import users as users_router
from src.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")


def create_app() -> FastAPI:
    app = FastAPI(
        title="HotelOS — auth-service",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )
    install_handlers(app)
    app.include_router(auth_router.router)
    app.include_router(users_router.router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    return app


app = create_app()
