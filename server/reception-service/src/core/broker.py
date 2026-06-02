"""Redis broker client.

We hold one async connection per process and reuse it for all publishes. The
client itself manages a small pool internally; we just need to open and close
it cleanly around the FastAPI lifespan.
"""

from __future__ import annotations

import redis.asyncio as redis

from src.core.config import settings


def create_redis() -> redis.Redis:
    """Return a configured but not-yet-connected Redis client.

    Decode responses so callers work with `str`, not `bytes` — payloads are
    JSON-encoded so we always want strings on the application boundary.
    """
    return redis.from_url(settings.redis_url, decode_responses=True)
