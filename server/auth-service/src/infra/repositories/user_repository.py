"""Data access for User + UserSettings."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.enums import UserRole
from src.domain.models import User, UserSettings


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_phone(self, phone: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.settings))
            .where(User.phone == phone)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).options(selectinload(User.settings)).where(User.id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_active(self, role: UserRole | None = None) -> list[User]:
        stmt = select(User).where(User.is_active.is_(True))
        if role is not None:
            stmt = stmt.where(User.role == role)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(
        self,
        *,
        phone: str,
        password_hash: str,
        role: UserRole,
        full_name: str | None = None,
        preferred_locale: str = "uz",
    ) -> User:
        user = User(
            phone=phone,
            password_hash=password_hash,
            role=role,
            full_name=full_name,
        )
        user.settings = UserSettings(preferred_locale=preferred_locale, extra={})
        self.session.add(user)
        await self.session.flush()
        return user
