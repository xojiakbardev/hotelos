"""Inbound event handlers for room-service.

All four order-lifecycle events go through here. Handlers are idempotent:
  * `on_order_received` upserts by primary key (the order id matches
     reception's), so a duplicate delivery is a no-op.
  * `on_order_advanced` only writes if the mirror's status is strictly
     behind the incoming one — re-orderings (Redis pub/sub is at-most-once
     but ordering between subscribers isn't guaranteed across processes)
     get ignored cleanly.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from src.core.db import async_session_factory
from src.domain.enums import OrderStatus
from src.infra.repositories.order_mirror_repository import OrderMirrorRepository

logger = logging.getLogger("room-service.handlers")

STATUS_ORDER: dict[OrderStatus, int] = {
    OrderStatus.RECEIVED: 0,
    OrderStatus.PREPARING: 1,
    OrderStatus.DELIVERING: 2,
    OrderStatus.DELIVERED: 3,
}


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


async def on_order_received(envelope: dict) -> None:
    payload = envelope.get("payload") or {}
    order_id = payload.get("order_id")
    guest_id = payload.get("guest_id")
    if not order_id or not guest_id:
        return
    async with async_session_factory() as session:
        async with session.begin():
            repo = OrderMirrorRepository(session)
            await repo.upsert_received(
                order_id=uuid.UUID(order_id),
                guest_id=uuid.UUID(guest_id),
                room_number=int(payload.get("room_number", 0)),
                floor=int(payload.get("floor", 0)),
                items=list(payload.get("items") or []),
                total_minor_units=int(payload.get("total_minor_units", 0)),
                taken_by_user_id=uuid.UUID(payload.get("taken_by_user_id", str(uuid.uuid4()))),
                received_at=_parse_dt(payload.get("received_at")),
            )


def make_on_advance(target: OrderStatus):
    """Factory — produces a handler bound to a specific target status."""

    async def _handler(envelope: dict) -> None:
        payload = envelope.get("payload") or {}
        raw_id = payload.get("order_id")
        if not raw_id:
            return
        transitioned_at = _parse_dt(payload.get("transitioned_at"))
        async with async_session_factory() as session:
            async with session.begin():
                repo = OrderMirrorRepository(session)
                order = await repo.get(uuid.UUID(raw_id))
                if order is None:
                    # The mirror missed `received` somehow — log and move on.
                    # The next event for this order will create it via
                    # `on_order_received`. We do NOT manufacture a row here
                    # because we don't have the items payload to project.
                    logger.warning("advance for unknown order %s, skipping", raw_id)
                    return
                current = OrderStatus(order.status)
                # Idempotency / out-of-order safety: only advance if the
                # incoming status is strictly later in the lifecycle.
                if STATUS_ORDER[target] <= STATUS_ORDER[current]:
                    return
                await repo.update_status(order, new_status=target, transitioned_at=transitioned_at)

    return _handler
