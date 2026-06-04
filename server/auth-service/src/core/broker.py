"""Redis broker client for auth-service."""

from __future__ import annotations

import redis.asyncio as redis

from src.core.config import settings


def create_redis() -> redis.Redis:
    """Return a configured but not-yet-connected Redis client."""
    return redis.from_url(settings.redis_url, decode_responses=True)
