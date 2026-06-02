"""Rooms inventory endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import SessionDep, require_role
from src.api.schemas.room import RoomList, RoomOut
from src.domain.enums import UserRole
from src.infra.repositories.room_repository import RoomRepository

router = APIRouter(prefix="/rooms", tags=["rooms"])

ALL_AUTHENTICATED = (
    UserRole.MANAGER,
    UserRole.RECEPTION,
    UserRole.TECHNICIAN,
    UserRole.CLEANER,
)


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
