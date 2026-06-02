"""Cleaning queue endpoints — visible to manager + cleaner roles.

Three actions matter:

  GET /queue                                — list open entries (pending +
                                              in_progress), oldest first.
  POST /queue/{entry_id}/start              — cleaner claims an entry and
                                              begins work. Publishes
                                              `rooms.cleaning_started`.
  POST /queue/{entry_id}/complete           — cleaner marks done. Publishes
                                              `rooms.cleaned`, which
                                              reception subscribes to and
                                              uses to flip the room back to
                                              clean + available.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import (
    CurrentUserDep,
    PublisherDep,
    SessionDep,
    require_role,
)
from src.api.schemas.queue import CleaningEntryOut
from src.domain.enums import CleaningStatus, UserRole
from src.events.topics import Channels
from src.infra.repositories.cleaning_queue_repository import CleaningQueueRepository

router = APIRouter(prefix="/queue", tags=["cleaning-queue"])

CAN_VIEW = (UserRole.MANAGER, UserRole.CLEANER)
CAN_WORK = (UserRole.MANAGER, UserRole.CLEANER)


@router.get("", response_model=list[CleaningEntryOut])
async def list_open_entries(
    session: SessionDep,
    _=Depends(require_role(*CAN_VIEW)),
) -> list[CleaningEntryOut]:
    entries = await CleaningQueueRepository(session).list_open()
    return [CleaningEntryOut.model_validate(e, from_attributes=True) for e in entries]


@router.post("/{entry_id}/start", response_model=CleaningEntryOut)
async def start_cleaning(
    entry_id: uuid.UUID,
    session: SessionDep,
    publisher: PublisherDep,
    user: CurrentUserDep,
    _=Depends(require_role(*CAN_WORK)),
) -> CleaningEntryOut:
    repo = CleaningQueueRepository(session)
    async with session.begin():
        entry = await repo.get(entry_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entry not found")
        if entry.status != CleaningStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "wrong_state",
                    "message": f"cannot start an entry in status '{entry.status}'",
                    "current_status": entry.status,
                },
            )
        await repo.mark_started(entry, cleaner_id=uuid.UUID(user.id))
        snapshot = CleaningEntryOut.model_validate(entry, from_attributes=True)

    await publisher.publish(
        channel=Channels.ROOM_CLEANING_STARTED,
        payload={
            "entry_id": str(snapshot.id),
            "room_id": str(snapshot.room_id),
            "room_number": snapshot.room_number,
            "floor": snapshot.floor,
            "cleaner_user_id": user.id,
            "started_at": (snapshot.started_at or datetime.now(timezone.utc)).isoformat(),
        },
    )
    return snapshot


@router.post("/{entry_id}/complete", response_model=CleaningEntryOut)
async def complete_cleaning(
    entry_id: uuid.UUID,
    session: SessionDep,
    publisher: PublisherDep,
    user: CurrentUserDep,
    _=Depends(require_role(*CAN_WORK)),
) -> CleaningEntryOut:
    repo = CleaningQueueRepository(session)
    async with session.begin():
        entry = await repo.get(entry_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="entry not found")
        if entry.status != CleaningStatus.IN_PROGRESS.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "wrong_state",
                    "message": f"cannot complete an entry in status '{entry.status}'",
                    "current_status": entry.status,
                },
            )
        await repo.mark_completed(entry)
        snapshot = CleaningEntryOut.model_validate(entry, from_attributes=True)

    await publisher.publish(
        channel=Channels.ROOM_CLEANED,
        payload={
            "entry_id": str(snapshot.id),
            "room_id": str(snapshot.room_id),
            "room_number": snapshot.room_number,
            "floor": snapshot.floor,
            "cleaner_user_id": user.id,
            "cleaned_at": (snapshot.completed_at or datetime.now(timezone.utc)).isoformat(),
        },
    )
    return snapshot
