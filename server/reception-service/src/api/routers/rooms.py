"""Rooms inventory endpoints.

Read access for every authenticated role; create / update / delete are
manager-only — only the manager can add new rooms or retire one. The
delete is hard-blocked while a guest is in residence (FK ON DELETE not
configured for that direction; the explicit 409 makes the error path
clearer than a Postgres constraint message bubbling up).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError

from src.api.dependencies import SessionDep, require_role
from src.api.schemas.room import RoomBulkCreate, RoomCreate, RoomList, RoomOut, RoomUpdate
from src.domain.enums import Cleanliness, RoomStatus, UserRole
from src.domain.models import Room
from src.infra.repositories.room_repository import RoomRepository

router = APIRouter(prefix="/rooms", tags=["rooms"])

ALL_AUTHENTICATED = (
    UserRole.MANAGER,
    UserRole.RECEPTION,
    UserRole.TECHNICIAN,
    UserRole.CLEANER,
    UserRole.KITCHEN,
)
MANAGER_ONLY = (UserRole.MANAGER,)


@router.get("", response_model=RoomList)
async def list_rooms(
    session: SessionDep,
    _=Depends(require_role(*ALL_AUTHENTICATED)),
) -> RoomList:
    """Return every room, ordered by room number. Every staff role can read
    this — what they can do with it is enforced at write-time.
    Freshness scores are recomputed live from last_cleaned_at."""
    from src.services.freshness import compute_dynamic_price, compute_freshness_score

    rooms = await RoomRepository(session).list_all()
    results: list[RoomOut] = []
    for r in rooms:
        # Recompute live freshness for clean+available rooms
        if r.cleanliness_status == Cleanliness.CLEAN.value and r.status == RoomStatus.AVAILABLE.value:
            score = compute_freshness_score(r.last_cleaned_at)
            r.freshness_score = score
            r.dynamic_price_minor_units = compute_dynamic_price(r.nightly_rate_minor_units, score)
        results.append(RoomOut.model_validate(r, from_attributes=True))
    return RoomList(rooms=results, total=len(results))


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


@router.post("/bulk", response_model=RoomList, status_code=status.HTTP_201_CREATED)
async def create_rooms_bulk(
    payload: RoomBulkCreate,
    session: SessionDep,
    _=Depends(require_role(*MANAGER_ONLY)),
) -> RoomList:
    # 1. Check for duplicate room numbers in the payload itself
    room_numbers = [r.room_number for r in payload.rooms]
    if len(room_numbers) != len(set(room_numbers)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "duplicate_room_number_in_payload",
                "message": "Duplicate room numbers in the creation list.",
            },
        )

    # 2. Check if any room number already exists in the database
    repo = RoomRepository(session)
    try:
        async with session.begin():
            existing_rooms = await repo.get_by_numbers(room_numbers)
            if existing_rooms:
                exist_nums = [r.room_number for r in existing_rooms]
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "duplicate_room_number",
                        "message": f"Rooms already exist: {exist_nums}",
                    },
                )

            created_rooms = []
            for r in payload.rooms:
                room = Room(
                    room_number=r.room_number,
                    floor=r.floor,
                    room_type=r.room_type.value,
                    proximity=r.proximity.value,
                    nightly_rate_minor_units=r.nightly_rate_minor_units,
                    cleanliness_status=Cleanliness.CLEAN.value,
                    status=RoomStatus.AVAILABLE.value,
                )
                session.add(room)
                created_rooms.append(room)

            await session.flush()
            rooms_out = [RoomOut.model_validate(r, from_attributes=True) for r in created_rooms]
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "duplicate_room_number",
                "message": "Some room numbers already exist in the database.",
            },
        ) from exc

    return RoomList(
        rooms=rooms_out,
        total=len(rooms_out),
    )





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


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_room(
    room_id: uuid.UUID,
    session: SessionDep,
    confirm: bool = False,
    _=Depends(require_role(*MANAGER_ONLY)),
) -> Response:
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

        # Check if room has related data (bills, guests, reservations, orders)
        has_history = await repo.has_related_data(room_id)

        if has_history and not confirm:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "room_has_history",
                    "requires_confirmation": True,
                    "message": (
                        "Bu xonaga bog'liq ma'lumotlar (mehmonlar tarixi, hisoblar, "
                        "bronlar, buyurtmalar) ham o'chiriladi. "
                        "Davom etishni tasdiqlaysizmi?"
                    ),
                },
            )

        try:
            await repo.delete_with_related(room) if has_history else await repo.delete(room)
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "room_has_history",
                    "requires_confirmation": True,
                    "message": (
                        "Bu xonaga bog'liq ma'lumotlar ham o'chiriladi. "
                        "?confirm=true qo'shib qayta yuboring."
                    ),
                },
            ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/freshness")
async def get_freshness(
    session: SessionDep,
    _=Depends(require_role(*ALL_AUTHENTICATED)),
) -> list[dict]:
    """Freshness score for every room — drives dynamic pricing display."""
    from src.services.freshness import compute_freshness_score, compute_dynamic_price

    rooms = await RoomRepository(session).list_all()
    result = []
    for r in rooms:
        score = compute_freshness_score(r.last_cleaned_at)
        dynamic = compute_dynamic_price(r.nightly_rate_minor_units, score)
        result.append({
            "room_id": str(r.id),
            "room_number": r.room_number,
            "freshness_score": score,
            "dynamic_price_minor_units": dynamic,
            "base_price_minor_units": r.nightly_rate_minor_units,
        })
    return result


@router.get("/pricing")
async def get_pricing(
    session: SessionDep,
    _=Depends(require_role(*ALL_AUTHENTICATED)),
) -> list[dict]:
    """Dynamic pricing for every room based on freshness."""
    from src.services.freshness import compute_freshness_score, compute_dynamic_price

    rooms = await RoomRepository(session).list_all()
    return [
        {
            "room_id": str(r.id),
            "room_number": r.room_number,
            "base_price_minor_units": r.nightly_rate_minor_units,
            "dynamic_price_minor_units": compute_dynamic_price(
                r.nightly_rate_minor_units,
                compute_freshness_score(r.last_cleaned_at),
            ),
        }
        for r in rooms
    ]
