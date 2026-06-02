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
