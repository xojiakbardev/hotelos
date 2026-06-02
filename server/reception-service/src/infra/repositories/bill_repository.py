"""Data access for finalised bills."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import Bill
from src.services.billing import BillSnapshot


class BillRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        guest_id: uuid.UUID,
        room_id: uuid.UUID,
        snapshot: BillSnapshot,
    ) -> Bill:
        bill = Bill(
            guest_id=guest_id,
            room_id=room_id,
            nights=snapshot.nights,
            nightly_rate_minor_units=snapshot.nightly_rate_minor_units,
            room_cost_minor_units=snapshot.room_cost_minor_units,
            room_service_charges_minor_units=snapshot.room_service_charges_minor_units,
            extras_minor_units=snapshot.extras_minor_units,
            discount_minor_units=snapshot.discount_minor_units,
            total_minor_units=snapshot.total_minor_units,
        )
        self.session.add(bill)
        await self.session.flush()
        return bill

    async def get(self, bill_id: uuid.UUID) -> Bill | None:
        return await self.session.get(Bill, bill_id)

    async def list_for_guest(self, guest_id: uuid.UUID) -> list[Bill]:
        stmt = select(Bill).where(Bill.guest_id == guest_id)
        return list((await self.session.execute(stmt)).scalars().all())
