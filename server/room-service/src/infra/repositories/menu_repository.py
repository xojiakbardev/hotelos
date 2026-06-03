"""Data access for the menu catalogue."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import MenuItem


class MenuRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, item_id: uuid.UUID) -> MenuItem | None:
        return await self.session.get(MenuItem, item_id)

    async def list_all(self, *, available_only: bool = False) -> list[MenuItem]:
        stmt = select(MenuItem).order_by(MenuItem.category.asc(), MenuItem.name.asc())
        if available_only:
            stmt = stmt.where(MenuItem.is_available.is_(True))
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(
        self,
        *,
        name: str,
        category: str,
        price_minor_units: int,
        prep_minutes: int,
        is_available: bool,
    ) -> MenuItem:
        item = MenuItem(
            name=name,
            category=category,
            price_minor_units=price_minor_units,
            prep_minutes=prep_minutes,
            is_available=is_available,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def update(
        self,
        item: MenuItem,
        *,
        name: str | None = None,
        category: str | None = None,
        price_minor_units: int | None = None,
        prep_minutes: int | None = None,
        is_available: bool | None = None,
    ) -> None:
        if name is not None:
            item.name = name
        if category is not None:
            item.category = category
        if price_minor_units is not None:
            item.price_minor_units = price_minor_units
        if prep_minutes is not None:
            item.prep_minutes = prep_minutes
        if is_available is not None:
            item.is_available = is_available
        await self.session.flush()

    async def delete(self, item: MenuItem) -> None:
        await self.session.delete(item)
        await self.session.flush()
