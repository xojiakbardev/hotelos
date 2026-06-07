"""Data access for the local technician projection."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import Technician


class TechnicianRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: uuid.UUID) -> Technician | None:
        return await self.session.get(Technician, user_id)

    async def upsert(
        self,
        *,
        user_id: uuid.UUID,
        full_name: str | None,
        phone: str,
        role: str,
        is_active: bool,
    ) -> Technician:
        existing = await self.session.get(Technician, user_id)
        if existing is None:
            existing = Technician(
                id=user_id,
                full_name=full_name,
                phone=phone,
                role=role,
                is_active=is_active,
            )
            self.session.add(existing)
        else:
            existing.full_name = full_name
            existing.phone = phone
            existing.role = role
            existing.is_active = is_active
        return existing

    async def deactivate(self, user_id: uuid.UUID) -> None:
        existing = await self.session.get(Technician, user_id)
        if existing is not None:
            existing.is_active = False
