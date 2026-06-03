"""Data access for reservations (future bookings)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.enums import ACTIVE_RESERVATION_STATUSES, ReservationStatus
from src.domain.models import Reservation, Room


class ReservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, reservation_id: uuid.UUID) -> Reservation | None:
        return await self.session.get(Reservation, reservation_id)

    async def list_all(
        self, *, status: ReservationStatus | None = None, limit: int = 200
    ) -> list[Reservation]:
        stmt = (
            select(Reservation)
            .order_by(Reservation.check_in_date.asc(), Reservation.created_at.desc())
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(Reservation.status == status.value)
        return list((await self.session.execute(stmt)).scalars().all())

    async def lock_room_and_check_conflict(
        self,
        *,
        room_id: uuid.UUID,
        check_in_date: date,
        check_out_date: date,
        exclude_reservation_id: uuid.UUID | None = None,
    ) -> Room | None:
        """Lock the candidate room row (FOR UPDATE) and return it ONLY if no
        active reservation already covers any of the requested dates.

        The FOR UPDATE on the room row serialises concurrent reservation
        creates for the same room — the second transaction waits, re-reads
        the conflict set, and sees the freshly-committed first reservation,
        so it returns `None` and the caller raises a 409.

        Date semantics: check-in is inclusive, check-out is exclusive — i.e.
        a guest checking out on Tuesday frees the room for that same Tuesday
        check-in. Overlap test reflects that with `<` not `<=`.
        """
        # Take the lock on the room first.
        room_stmt = select(Room).where(Room.id == room_id).with_for_update()
        room = (await self.session.execute(room_stmt)).scalar_one_or_none()
        if room is None:
            return None

        # Active reservations whose dates overlap with [check_in, check_out).
        overlap = and_(
            Reservation.room_id == room_id,
            Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
            Reservation.check_in_date < check_out_date,
            Reservation.check_out_date > check_in_date,
        )
        conflict_stmt = select(Reservation.id).where(overlap)
        if exclude_reservation_id is not None:
            conflict_stmt = conflict_stmt.where(Reservation.id != exclude_reservation_id)

        conflict = (await self.session.execute(conflict_stmt)).first()
        if conflict is not None:
            return None
        return room

    async def create(
        self,
        *,
        full_name: str,
        phone: str,
        passport_number: str | None,
        room_id: uuid.UUID,
        check_in_date: date,
        check_out_date: date,
        nightly_rate_locked_minor_units: int,
    ) -> Reservation:
        reservation = Reservation(
            full_name=full_name,
            phone=phone,
            passport_number=passport_number,
            room_id=room_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            nightly_rate_locked_minor_units=nightly_rate_locked_minor_units,
            status=ReservationStatus.PENDING.value,
        )
        self.session.add(reservation)
        await self.session.flush()
        return reservation

    async def transition(
        self,
        reservation: Reservation,
        *,
        new_status: ReservationStatus,
        guest_id: uuid.UUID | None = None,
    ) -> None:
        reservation.status = new_status.value
        reservation.status_changed_at = datetime.now(timezone.utc)
        if guest_id is not None:
            reservation.guest_id = guest_id
        await self.session.flush()

    async def list_with_room(
        self, *, status: ReservationStatus | None = None, limit: int = 200
    ) -> list[Reservation]:
        stmt = (
            select(Reservation)
            .options(selectinload(Reservation.room))  # type: ignore[arg-type]
            .order_by(Reservation.check_in_date.asc(), Reservation.created_at.desc())
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(Reservation.status == status.value)
        return list((await self.session.execute(stmt)).scalars().all())
