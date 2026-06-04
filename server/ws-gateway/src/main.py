"""ws-gateway: a single WebSocket endpoint per browser, fed by Redis Pub/Sub.

Each connected client:
  1. Authenticates via the same JWT the REST services accept (passed as ?token=...).
  2. Subscribes to Redis pattern channels appropriate for their role.
  3. Receives JSON frames whose payloads have been role-redacted.

The browser does not need to know which microservice owned an event — it just
reads `{type, payload}` and updates its Pinia store.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt

from src.config import settings
from src.roles import channel_matches, channels_for, event_targets_guest, redact

logger = logging.getLogger("ws-gateway")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("ws-gateway started, connected to redis at %s", settings.redis_url)
    try:
        yield
    finally:
        await app.state.redis.aclose()


app = FastAPI(title="HotelOS — ws-gateway", version="0.1.0", lifespan=lifespan)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


def _decode(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


async def _pump(
    ws: WebSocket,
    pubsub,
    allowed_patterns: list[str],
    role: str,
    guest_id: str | None = None,
    room_id: str | None = None,
) -> None:
    """Drain redis pubsub messages into the WebSocket, role-redacting along the way."""
    async for message in pubsub.listen():
        if message is None or message.get("type") != "pmessage":
            continue
        channel = message["channel"]
        if not channel_matches(channel, allowed_patterns):
            continue
        try:
            envelope = json.loads(message["data"])
        except json.JSONDecodeError:
            logger.warning("dropping malformed event on %s", channel)
            continue
        envelope.setdefault("payload", {})
        # Guests only receive events targeting their own room/guest_id.
        if role == "guest" and not event_targets_guest(
            envelope["payload"], guest_id, room_id
        ):
            continue
        envelope["payload"] = redact(envelope["payload"], role)
        envelope["channel"] = channel
        try:
            await ws.send_json(envelope)
        except WebSocketDisconnect:
            break
        except RuntimeError:
            break


@app.websocket("/ws")
async def ws_root(ws: WebSocket, token: str | None = Query(default=None)) -> None:
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        claims = _decode(token)
    except JWTError:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    role = str(claims.get("role", ""))
    allowed = channels_for(role)
    if not allowed:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    guest_id = str(claims.get("guest_id")) if claims.get("guest_id") else None
    room_id = str(claims.get("room_id")) if claims.get("room_id") else None
    auth_user_id = str(claims.get("sub", ""))

    await ws.accept()
    await ws.send_json({"type": "connection_ack", "role": role, "channels": allowed})

    pubsub = ws.app.state.redis.pubsub()
    await pubsub.psubscribe(*allowed)
    # Guests also subscribe to credential deactivation so we can force-close
    # their socket the moment they are checked out.
    if role == "guest":
        await pubsub.psubscribe("guests.credential_deactivated")

    pump_task = asyncio.create_task(
        _pump(ws, pubsub, allowed, role, guest_id, room_id)
    )

    # For guests, watch for their own deactivation event in a side task.
    deact_task = None
    if role == "guest":
        deact_task = asyncio.create_task(
            _watch_deactivation(ws, ws.app.state.redis, auth_user_id)
        )

    try:
        while True:
            # Keep the inbound side draining so the underlying TCP doesn't stall.
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        pump_task.cancel()
        if deact_task is not None:
            deact_task.cancel()
        await pubsub.punsubscribe()
        await pubsub.aclose()


async def _watch_deactivation(ws: WebSocket, client, auth_user_id: str) -> None:
    """Close the guest WS when their credential is deactivated at check-out."""
    pubsub = client.pubsub()
    await pubsub.subscribe("guests.credential_deactivated")
    try:
        async for message in pubsub.listen():
            if message is None or message.get("type") != "message":
                continue
            try:
                envelope = json.loads(message["data"])
            except json.JSONDecodeError:
                continue
            payload = envelope.get("payload", {})
            if str(payload.get("auth_user_id", "")) == auth_user_id:
                try:
                    await ws.close(code=status.WS_1008_POLICY_VIOLATION)
                except RuntimeError:
                    pass
                break
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()
