"""Data access for the cleaning queue."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import CleaningStatus
from src.domain.models import CleaningQueueEntry


class CleaningQueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entry_id: uuid.UUID) -> CleaningQueueEntry | None:
        return await self.session.get(CleaningQueueEntry, entry_id)

    async def find_active_for_room(self, room_id: uuid.UUID) -> CleaningQueueEntry | None:
        """Return the open queue entry for this room (pending or in_progress),
        if any. Used by the room.vacated subscriber to deduplicate replays."""
        stmt = select(CleaningQueueEntry).where(
            CleaningQueueEntry.room_id == room_id,
            CleaningQueueEntry.status.in_(
                (CleaningStatus.PENDING.value, CleaningStatus.IN_PROGRESS.value)
            ),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_open(self) -> list[CleaningQueueEntry]:
        """All entries not yet completed, FIFO order (oldest queued first).
        This is exactly the brief's "queue" — head of the list is next."""
        stmt = (
            select(CleaningQueueEntry)
            .where(CleaningQueueEntry.status != CleaningStatus.COMPLETED.value)
            .order_by(CleaningQueueEntry.queued_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def enqueue(
        self, *, room_id: uuid.UUID, room_number: int, floor: int
    ) -> CleaningQueueEntry:
        entry = CleaningQueueEntry(
            room_id=room_id,
            room_number=room_number,
            floor=floor,
            status=CleaningStatus.PENDING.value,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def mark_started(
        self, entry: CleaningQueueEntry, *, cleaner_id: uuid.UUID
    ) -> None:
        entry.status = CleaningStatus.IN_PROGRESS.value
        entry.assigned_cleaner_id = cleaner_id
        entry.started_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def mark_completed(self, entry: CleaningQueueEntry) -> None:
        entry.status = CleaningStatus.COMPLETED.value
        entry.completed_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def set_dnd_for_room(self, room_id: uuid.UUID, value: bool) -> bool:
        """Update DND on the *active* queue entry for a room (if any).
        Returns True if a row was updated. No-op if the room isn't in the
        queue right now — a future enqueue will start with default False."""
        entry = await self.find_active_for_room(room_id)
        if entry is None:
            return False
        entry.do_not_disturb = value
        await self.session.flush()
        return True

    async def set_preference_for_room(
        self, room_id: uuid.UUID, *, preference: str, note: str | None
    ) -> bool:
        entry = await self.find_active_for_room(room_id)
        if entry is None:
            return False
        entry.cleaning_preference = preference
        entry.cleaning_preference_note = note
        await self.session.flush()
        return True
