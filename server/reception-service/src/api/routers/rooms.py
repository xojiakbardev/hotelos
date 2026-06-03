"""Rooms inventory endpoints.

Read access for every authenticated role; create / update / delete are
manager-only — only the manager can add new rooms or retire one. The
delete is hard-blocked while a guest is in residence (FK ON DELETE not
configured for that direction; the explicit 409 makes the error path
clearer than a Postgres constraint message bubbling up).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.api.dependencies import SessionDep, require_role
from src.api.schemas.room import RoomCreate, RoomList, RoomOut, RoomUpdate
from src.domain.enums import Cleanliness, RoomStatus, UserRole
from src.domain.models import Room
from src.infra.repositories.room_repository import RoomRepository

router = APIRouter(prefix="/rooms", tags=["rooms"])

ALL_AUTHENTICATED = (
    UserRole.MANAGER,
    UserRole.RECEPTION,
    UserRole.TECHNICIAN,
    UserRole.CLEANER,
)
MANAGER_ONLY = (UserRole.MANAGER,)


@router.get("", response_model=RoomList)
async def list_rooms(
    session: SessionDep,
    _=Depends(require_role(*ALL_AUTHENTICATED)),
) -> RoomList:
    """Return every room, ordered by room number. Every staff role can read
    this — what they can do with it is enforced at write-time."""
    rooms = await RoomRepository(session).list_all()
    return RoomList(
        rooms=[RoomOut.model_validate(r, from_attributes=True) for r in rooms],
        total=len(rooms),
    )


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreate,
    session: SessionDep,
    _=Depends(require_role(*MANAGER_ONLY)),
) -> RoomOut:
    room = Room(
        room_number=payload.room_number,
        floor=payload.floor,
        room_type=payload.room_type.value,
        proximity=payload.proximity.value,
        nightly_rate_minor_units=payload.nightly_rate_minor_units,
        # Fresh rooms start clean + available; lifecycle takes over from there.
        cleanliness_status=Cleanliness.CLEAN.value,
        status=RoomStatus.AVAILABLE.value,
    )
    repo = RoomRepository(session)
    try:
        async with session.begin():
            await repo.add(room)
            snapshot = RoomOut.model_validate(room, from_attributes=True)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "duplicate_room_number",
                "message": f"room {payload.room_number} already exists",
            },
        ) from exc
    return snapshot


@router.put("/{room_id}", response_model=RoomOut)
async def update_room(
    room_id: uuid.UUID,
    payload: RoomUpdate,
    session: SessionDep,
    _=Depends(require_role(*MANAGER_ONLY)),
) -> RoomOut:
    repo = RoomRepository(session)
    async with session.begin():
        room = await repo.get(room_id)
        if room is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="room not found")
        await repo.update_fields(
            room,
            floor=payload.floor,
            room_type=payload.room_type.value if payload.room_type else None,
            proximity=payload.proximity.value if payload.proximity else None,
            nightly_rate_minor_units=payload.nightly_rate_minor_units,
        )
        snapshot = RoomOut.model_validate(room, from_attributes=True)
    return snapshot


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: uuid.UUID,
    session: SessionDep,
    _=Depends(require_role(*MANAGER_ONLY)),
) -> None:
    repo = RoomRepository(session)
    async with session.begin():
        room = await repo.get(room_id)
        if room is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="room not found")
        if room.status == RoomStatus.OCCUPIED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "room_occupied",
                    "message": "check the guest out before deleting this room",
                },
            )
        try:
            await repo.delete(room)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "room_has_history",
                    "message": (
                        "room is referenced by past bookings or bills — "
                        "consider marking it out of service instead"
                    ),
                },
            ) from exc
