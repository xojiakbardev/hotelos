"""Data access for the rooms inventory."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import Cleanliness, RoomStatus, RoomType
from src.domain.models import Room


class RoomRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[Room]:
        stmt = select(Room).order_by(Room.room_number.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, room_id: uuid.UUID) -> Room | None:
        return await self.session.get(Room, room_id)

    async def find_assignable(
        self, *, room_type: RoomType, limit: int = 20
    ) -> list[Room]:
        """Candidate rooms for an incoming check-in.

        Returns clean + available rooms of the requested type, oldest-cleaned
        first, with each row LOCKed FOR UPDATE so two simultaneous check-ins
        can't pick the same row. `SKIP LOCKED` makes the second transaction
        pick the *next* free room instead of blocking — this is what protects
        TS-06 (concurrent same-type check-ins) from deadlocking the system.
        """
        stmt = (
            select(Room)
            .where(
                Room.room_type == room_type.value,
                Room.cleanliness_status == Cleanliness.CLEAN.value,
                Room.status == RoomStatus.AVAILABLE.value,
            )
            .order_by(Room.last_cleaned_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def lock_specific_assignable(self, room_id: uuid.UUID) -> Room | None:
        """Lock and return one specific room IF it is currently assignable
        (clean + available). Used when a receptionist clicks a specific room
        card rather than letting the algorithm choose.

        Returns None if the room is occupied, dirty, in maintenance, or
        already locked by another concurrent transaction.
        """
        stmt = (
            select(Room)
            .where(
                Room.id == room_id,
                Room.cleanliness_status == Cleanliness.CLEAN.value,
                Room.status == RoomStatus.AVAILABLE.value,
            )
            .with_for_update(skip_locked=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def mark_occupied(self, room: Room) -> None:
        room.status = RoomStatus.OCCUPIED.value
        room.last_assigned_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def add(self, room: Room) -> Room:
        self.session.add(room)
        await self.session.flush()
        return room

    async def update_fields(
        self,
        room: Room,
        *,
        floor: int | None = None,
        room_type: str | None = None,
        proximity: str | None = None,
        nightly_rate_minor_units: int | None = None,
    ) -> None:
        if floor is not None:
            room.floor = floor
        if room_type is not None:
            room.room_type = room_type
        if proximity is not None:
            room.proximity = proximity
        if nightly_rate_minor_units is not None:
            room.nightly_rate_minor_units = nightly_rate_minor_units
        await self.session.flush()

    async def delete(self, room: Room) -> None:
        await self.session.delete(room)
        await self.session.flush()

    async def get_by_numbers(self, numbers: list[int]) -> list[Room]:
        stmt = select(Room).where(Room.room_number.in_(numbers))
        return list((await self.session.execute(stmt)).scalars().all())


    async def has_related_data(self, room_id: uuid.UUID) -> bool:
        """Check if a room has any related guest, bill, order, or reservation data."""
        from src.domain.models import Bill, Guest, Order, Reservation

        for model, col in [
            (Guest, Guest.room_id),
            (Bill, Bill.room_id),
            (Order, Order.room_id),
            (Reservation, Reservation.room_id),
        ]:
            stmt = select(model.id).where(col == room_id).limit(1)
            result = (await self.session.execute(stmt)).scalar_one_or_none()
            if result is not None:
                return True
        return False

    async def delete_with_related(self, room: Room) -> None:
        """Delete a room and all its related data (confirmed by user).

        Deletion order matters because of FK constraints:
        orders → bills → guests → reservations → room
        """
        from sqlalchemy import delete as sql_delete
        from src.domain.models import Bill, CleaningRequest, Guest, Order, Reservation

        room_id = room.id

        # Delete orders (FK → guests, rooms)
        await self.session.execute(
            sql_delete(Order).where(Order.room_id == room_id)
        )
        # Delete bills (FK → guests, rooms)
        await self.session.execute(
            sql_delete(Bill).where(Bill.room_id == room_id)
        )
        # Delete cleaning requests (FK → guests, rooms)
        await self.session.execute(
            sql_delete(CleaningRequest).where(CleaningRequest.room_id == room_id)
        )
        # Delete guests (FK → rooms)
        await self.session.execute(
            sql_delete(Guest).where(Guest.room_id == room_id)
        )
        # Delete reservations (FK → rooms)
        await self.session.execute(
            sql_delete(Reservation).where(Reservation.room_id == room_id)
        )
        # Finally delete the room itself
        await self.session.delete(room)
        await self.session.flush()
