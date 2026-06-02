"""Data access for the kitchen-side order mirror."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import OrderStatus
from src.domain.models import OrderMirror


class OrderMirrorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, order_id: uuid.UUID) -> OrderMirror | None:
        return await self.session.get(OrderMirror, order_id)

    async def list_open(self) -> list[OrderMirror]:
        stmt = (
            select(OrderMirror)
            .where(OrderMirror.status != OrderStatus.DELIVERED.value)
            .order_by(OrderMirror.received_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_all(self, limit: int = 200) -> list[OrderMirror]:
        stmt = select(OrderMirror).order_by(OrderMirror.received_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def upsert_received(
        self,
        *,
        order_id: uuid.UUID,
        guest_id: uuid.UUID,
        room_number: int,
        floor: int,
        items: list[dict],
        total_minor_units: int,
        taken_by_user_id: uuid.UUID,
        received_at: datetime,
    ) -> OrderMirror:
        existing = await self.get(order_id)
        if existing is not None:
            return existing
        order = OrderMirror(
            id=order_id,
            guest_id=guest_id,
            room_number=room_number,
            floor=floor,
            status=OrderStatus.RECEIVED.value,
            items=items,
            total_minor_units=total_minor_units,
            taken_by_user_id=taken_by_user_id,
            received_at=received_at,
        )
        self.session.add(order)
        await self.session.flush()
        return order

    async def update_status(
        self, order: OrderMirror, *, new_status: OrderStatus, transitioned_at: datetime
    ) -> None:
        order.status = new_status.value
        if new_status is OrderStatus.PREPARING:
            order.preparing_at = transitioned_at
        elif new_status is OrderStatus.DELIVERING:
            order.delivering_at = transitioned_at
        elif new_status is OrderStatus.DELIVERED:
            order.delivered_at = transitioned_at
        await self.session.flush()
