"""Event publisher.

Wraps Redis Pub/Sub with the canonical HotelOS envelope:

    {
        "event":       <channel>,
        "version":     1,
        "occurred_at": "<ISO-8601 UTC>",
        "publisher":   "housekeeping-service",
        "trace_id":    "<from inbound request>",  // optional
        "payload":     { ... domain fields ... }
    }

ws-gateway and other subscribers expect exactly this shape.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger("housekeeping-service.publisher")


class EventPublisher:
    def __init__(self, client: redis.Redis, publisher_name: str) -> None:
        self._client = client
        self._publisher = publisher_name

    async def publish(
        self,
        *,
        channel: str,
        payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        envelope: dict[str, Any] = {
            "event": channel,
            "version": 1,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "publisher": self._publisher,
            "payload": payload,
        }
        if trace_id:
            envelope["trace_id"] = trace_id
        try:
            await self._client.publish(channel, json.dumps(envelope, default=str))
        except Exception:
            # Publishing failures must not break the inbound request — log and
            # move on. The DB transaction has already committed; subscribers
            # will catch up via the next reconciling event or a manual replay.
            logger.exception("failed to publish %s", channel)
