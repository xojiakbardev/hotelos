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

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from src.api.dependencies import (
    CurrentUserDep,
    PublisherDep,
    SessionDep,
    require_role,
)
from src.api.schemas.queue import CleaningEntryOut
from src.domain.enums import CleaningStatus, UserRole
from src.domain.models import CleaningQueueEntry, SystemSettings
from src.events.topics import Channels
from src.infra.repositories.cleaning_queue_repository import CleaningQueueRepository
from src.services.photo_storage import save_photo, validate_image

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


class ManualEnqueuePayload(BaseModel):
    room_id: uuid.UUID
    room_number: int = Field(..., ge=1, le=9999)
    floor: int = Field(..., ge=1, le=99)
    cleaning_preference: str = Field("afternoon", max_length=16)
    cleaning_preference_note: str | None = Field(None, max_length=200)


@router.post("", response_model=CleaningEntryOut, status_code=status.HTTP_201_CREATED)
async def enqueue_manual(
    payload: ManualEnqueuePayload,
    session: SessionDep,
    publisher: PublisherDep,
    user: CurrentUserDep,
    _=Depends(require_role(UserRole.MANAGER)),
) -> CleaningEntryOut:
    """Manager manually adds a room to the cleaning queue.

    The unique constraint (`room_id`, `status`) prevents creating a duplicate
    active entry — if the room already has a pending/in_progress entry we
    return that one instead of erroring.
    """
    repo = CleaningQueueRepository(session)
    async with session.begin():
        existing = await repo.find_active_for_room(payload.room_id)
        if existing is not None:
            snapshot = CleaningEntryOut.model_validate(existing, from_attributes=True)
        else:
            entry = CleaningQueueEntry(
                room_id=payload.room_id,
                room_number=payload.room_number,
                floor=payload.floor,
                status=CleaningStatus.PENDING.value,
                cleaning_preference=payload.cleaning_preference,
                cleaning_preference_note=payload.cleaning_preference_note,
            )
            session.add(entry)
            await session.flush()
            snapshot = CleaningEntryOut.model_validate(entry, from_attributes=True)

    await publisher.publish(
        channel=Channels.ROOM_CLEANING_REQUESTED,
        payload={
            "entry_id": str(snapshot.id),
            "room_id": str(snapshot.room_id),
            "room_number": snapshot.room_number,
            "floor": snapshot.floor,
            "requested_by_user_id": user.id,
        },
    )
    return snapshot


@router.get("/history", response_model=list[CleaningEntryOut])
async def list_completed_entries(
    session: SessionDep,
    _=Depends(require_role(*CAN_VIEW)),
) -> list[CleaningEntryOut]:
    """Completed cleaning entries (history) — newest first, includes photos."""
    entries = await CleaningQueueRepository(session).list_completed()
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
    photo: UploadFile | None = File(None),
) -> CleaningEntryOut:
    # Check if photo is required
    setting = await session.get(SystemSettings, "photo_required")
    photo_required = setting.value == "true" if setting else True

    if photo_required and photo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rasm yuklash majburiy",
        )

    photo_path: str | None = None
    if photo:
        await validate_image(photo)

    repo = CleaningQueueRepository(session)
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

    if photo:
        photo_path = await save_photo(photo, entry.room_id)
        entry.photo_path = photo_path

    await repo.mark_completed(entry)
    await session.commit()
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
            "photo_path": photo_path,
        },
    )
    return snapshot



# ---- Settings endpoints ----

@router.get("/settings")
async def get_settings(
    session: SessionDep,
    _=Depends(require_role(*CAN_VIEW)),
) -> dict:
    """Return housekeeping system settings."""
    setting = await session.get(SystemSettings, "photo_required")
    return {"photo_required": setting.value == "true" if setting else True}


@router.put("/settings")
async def update_settings(
    payload: dict,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(UserRole.MANAGER)),
) -> dict:
    """Update housekeeping system settings (manager only)."""
    photo_required = payload.get("photo_required")
    if photo_required is None:
        raise HTTPException(status_code=422, detail="photo_required field required")

    async with session.begin():
        setting = await session.get(SystemSettings, "photo_required")
        if setting:
            setting.value = "true" if photo_required else "false"
        else:
            session.add(SystemSettings(key="photo_required", value="true" if photo_required else "false"))

    await publisher.publish(
        channel=Channels.HOUSEKEEPING_SETTINGS_CHANGED,
        payload={"photo_required": bool(photo_required)},
    )
    return {"photo_required": bool(photo_required)}


# ---- Photo serving endpoint ----

@router.get("/photos/{file_path:path}")
async def serve_photo(
    file_path: str,
    _=Depends(require_role(UserRole.MANAGER, UserRole.CLEANER)),
):
    """Serve a cleaning proof photo."""
    from fastapi.responses import FileResponse
    from pathlib import Path

    full_path = Path("/app/uploads") / file_path
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="photo not found")

    # Security: ensure path doesn't escape uploads directory
    try:
        full_path.resolve().relative_to(Path("/app/uploads").resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="forbidden")

    return FileResponse(full_path)
