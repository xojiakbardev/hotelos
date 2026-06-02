"""Data access for room-service orders (owned by reception)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import OrderStatus
from src.domain.models import Order


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, order_id: uuid.UUID) -> Order | None:
        return await self.session.get(Order, order_id)

    async def list_open(self) -> list[Order]:
        """All orders not yet delivered, oldest first (a FIFO queue for the
        kitchen)."""
        stmt = (
            select(Order)
            .where(Order.status != OrderStatus.DELIVERED.value)
            .order_by(Order.received_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_delivered_for_guest(self, guest_id: uuid.UUID) -> list[Order]:
        """Used by the billing algorithm to compute the room-service charges."""
        stmt = select(Order).where(
            Order.guest_id == guest_id,
            Order.status == OrderStatus.DELIVERED.value,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_guest(self, guest_id: uuid.UUID) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.guest_id == guest_id)
            .order_by(Order.received_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(
        self,
        *,
        guest_id: uuid.UUID,
        room_id: uuid.UUID,
        room_number: int,
        floor: int,
        items: list[dict],
        total_minor_units: int,
        taken_by_user_id: uuid.UUID,
    ) -> Order:
        order = Order(
            guest_id=guest_id,
            room_id=room_id,
            room_number=room_number,
            floor=floor,
            status=OrderStatus.RECEIVED.value,
            items=items,
            total_minor_units=total_minor_units,
            taken_by_user_id=taken_by_user_id,
        )
        self.session.add(order)
        await self.session.flush()
        return order

    async def set_status(self, order: Order, new_status: OrderStatus) -> None:
        order.status = new_status.value
        now = datetime.now(timezone.utc)
        if new_status is OrderStatus.PREPARING:
            order.preparing_at = now
        elif new_status is OrderStatus.DELIVERING:
            order.delivering_at = now
        elif new_status is OrderStatus.DELIVERED:
            order.delivered_at = now
        await self.session.flush()
