"""Data access for guests — the dictionary/map of active stays."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.models import Guest


class GuestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, guest_id: uuid.UUID) -> Guest | None:
        stmt = (
            select(Guest)
            .options(selectinload(Guest.room))
            .where(Guest.id == guest_id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_active(self) -> list[Guest]:
        """All currently-checked-in guests."""
        stmt = (
            select(Guest)
            .options(selectinload(Guest.room))
            .where(Guest.checked_out_at.is_(None))
            .order_by(Guest.checked_in_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def daily_checkin_counts(self, days: int = 30) -> list[tuple[date, int]]:
        """Return [(day, count), …] for the last `days` calendar days, with
        zero rows included for empty days.

        Used by the dashboard's "guests over time" chart. We do the
        gap-filling here (rather than in the route handler) so the API
        always returns a clean dense series.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days - 1)
        # Cast `checked_in_at` to a calendar date so guests checked in on
        # the same day are bucketed together. Postgres uses session TZ —
        # the container default is UTC.
        day_col = func.date(Guest.checked_in_at).label("day")
        stmt = (
            select(day_col, func.count(Guest.id).label("n"))
            .where(Guest.checked_in_at >= cutoff)
            .group_by(day_col)
        )
        rows = (await self.session.execute(stmt)).all()
        counts: dict[date, int] = {r.day: int(r.n) for r in rows}

        today = datetime.now(timezone.utc).date()
        out: list[tuple[date, int]] = []
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            out.append((d, counts.get(d, 0)))
        return out

    async def create(
        self,
        *,
        full_name: str,
        phone: str,
        passport_number: str | None,
        room_id: uuid.UUID,
        expected_checkout_at: datetime,
        nightly_rate_locked_minor_units: int,
        cleaning_preference: str = "afternoon",
        cleaning_preference_note: str | None = None,
        auth_user_id: uuid.UUID | None = None,
    ) -> Guest:
        guest = Guest(
            full_name=full_name,
            phone=phone,
            passport_number=passport_number,
            room_id=room_id,
            expected_checkout_at=expected_checkout_at,
            nightly_rate_locked_minor_units=nightly_rate_locked_minor_units,
            cleaning_preference=cleaning_preference,
            cleaning_preference_note=cleaning_preference_note,
            auth_user_id=auth_user_id,
        )
        self.session.add(guest)
        await self.session.flush()
        return guest

    async def set_dnd(self, guest: Guest, value: bool) -> None:
        guest.do_not_disturb = value
        await self.session.flush()

    async def set_cleaning_preference(
        self,
        guest: Guest,
        *,
        preference: str,
        note: str | None,
    ) -> None:
        guest.cleaning_preference = preference
        guest.cleaning_preference_note = note
        await self.session.flush()

    async def list_by_phone(self, phone: str) -> list[Guest]:
        """All historical stays for a given phone number, newest first.

        Each Guest row is a single stay, so "loyalty" is an aggregate over
        the rows that share a phone. We use phone instead of a stable
        guest_id because the system never asks for a separate registration.
        """
        stmt = (
            select(Guest)
            .options(selectinload(Guest.room), selectinload(Guest.bills))
            .where(Guest.phone == phone)
            .order_by(Guest.checked_in_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())
