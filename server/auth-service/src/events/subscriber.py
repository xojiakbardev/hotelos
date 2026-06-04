"""Redis Pub/Sub subscriber for auth-service.

Same pattern as reception-service's EventSubscriber — register handlers,
start a background asyncio task, dispatch incoming messages.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable

import redis.asyncio as redis

logger = logging.getLogger("auth-service.subscriber")

Handler = Callable[[dict], Awaitable[None]]


class EventSubscriber:
    def __init__(self, client: redis.Redis) -> None:
        self._client = client
        self._handlers: dict[str, list[Handler]] = {}
        self._task: asyncio.Task | None = None
        self._pubsub: redis.client.PubSub | None = None

    def on(self, channel: str, handler: Handler) -> None:
        self._handlers.setdefault(channel, []).append(handler)

    async def start(self) -> None:
        if self._task is not None:
            return
        self._pubsub = self._client.pubsub()
        if self._handlers:
            await self._pubsub.subscribe(*self._handlers.keys())
        self._task = asyncio.create_task(self._loop(), name="auth-subscriber")
        logger.info("subscriber started, channels=%s", list(self._handlers))

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._pubsub is not None:
            try:
                await self._pubsub.unsubscribe()
            finally:
                await self._pubsub.aclose()
            self._pubsub = None

    async def _loop(self) -> None:
        assert self._pubsub is not None
        try:
            async for message in self._pubsub.listen():
                if message is None or message.get("type") != "message":
                    continue
                channel = message["channel"]
                try:
                    envelope = json.loads(message["data"])
                except json.JSONDecodeError:
                    logger.warning("malformed event on %s", channel)
                    continue
                for handler in self._handlers.get(channel, []):
                    try:
                        await handler(envelope)
                    except Exception:
                        logger.exception("handler failed for %s", channel)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("subscriber loop crashed")
            raise
