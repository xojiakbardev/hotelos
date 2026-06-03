"""Reservation endpoints.

Lifecycle: PENDING → CONFIRMED → CHECKED_IN. Side-tracks: CANCELLED, NO_SHOW.

Race-condition guard: `lock_room_and_check_conflict` takes a row-level FOR
UPDATE lock on the candidate room before checking the overlap. Two concurrent
reservation attempts for the same room serialise — the loser sees the
freshly-committed first row and gets a structured 409.

This is the TS-06 path the brief specifically asks for ("double-booking
under concurrency"). The walk-in check-in flow already uses FOR UPDATE
SKIP LOCKED on the rooms table; this complements it for forward bookings.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import PublisherDep, SessionDep, require_role
from src.api.schemas.guest import GuestOut
from src.api.schemas.reservation import (
    ReservationCheckInRequest,
    ReservationCreate,
    ReservationOut,
)
from src.domain.enums import (
    Cleanliness,
    ReservationStatus,
    RoomStatus,
    UserRole,
)
from src.events.topics import Channels
from src.infra.repositories.guest_repository import GuestRepository
from src.infra.repositories.reservation_repository import ReservationRepository
from src.infra.repositories.room_repository import RoomRepository

router = APIRouter(prefix="/reservations", tags=["reservations"])

CAN_MANAGE = (UserRole.MANAGER, UserRole.RECEPTION)


def _to_out(reservation) -> ReservationOut:
    return ReservationOut(
        id=reservation.id,
        full_name=reservation.full_name,
        phone=reservation.phone,
        passport_number=reservation.passport_number,
        room_id=reservation.room_id,
        room_number=reservation.room.room_number,
        floor=reservation.room.floor,
        check_in_date=reservation.check_in_date,
        check_out_date=reservation.check_out_date,
        status=reservation.status,
        nightly_rate_locked_minor_units=reservation.nightly_rate_locked_minor_units,
        guest_id=reservation.guest_id,
        status_changed_at=reservation.status_changed_at,
        created_at=reservation.created_at,
    )


@router.get("", response_model=list[ReservationOut])
async def list_reservations(
    session: SessionDep,
    status_filter: ReservationStatus | None = None,
    _=Depends(require_role(*CAN_MANAGE)),
) -> list[ReservationOut]:
    repo = ReservationRepository(session)
    rows = await repo.list_with_room(status=status_filter)
    return [_to_out(r) for r in rows]


@router.post("", response_model=ReservationOut, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    payload: ReservationCreate,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(*CAN_MANAGE)),
) -> ReservationOut:
    repo = ReservationRepository(session)
    async with session.begin():
        room = await repo.lock_room_and_check_conflict(
            room_id=payload.room_id,
            check_in_date=payload.check_in_date,
            check_out_date=payload.check_out_date,
        )
        if room is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "room_unavailable_for_dates",
                    "message": (
                        "this room is already reserved (or doesn't exist) "
                        "for one or more of the requested dates"
                    ),
                    "room_id": str(payload.room_id),
                    "check_in_date": payload.check_in_date.isoformat(),
                    "check_out_date": payload.check_out_date.isoformat(),
                },
            )
        reservation = await repo.create(
            full_name=payload.full_name,
            phone=payload.phone,
            passport_number=payload.passport_number,
            room_id=room.id,
            check_in_date=payload.check_in_date,
            check_out_date=payload.check_out_date,
            nightly_rate_locked_minor_units=room.nightly_rate_minor_units,
        )
        # Reload with the room relationship populated for the response.
        reservation.room = room  # avoids an extra query

    await publisher.publish(
        channel=Channels.RESERVATION_CREATED,
        payload={
            "reservation_id": str(reservation.id),
            "room_id": str(reservation.room_id),
            "room_number": room.room_number,
            "check_in_date": reservation.check_in_date.isoformat(),
            "check_out_date": reservation.check_out_date.isoformat(),
        },
    )
    return _to_out(reservation)


@router.post("/{reservation_id}/confirm", response_model=ReservationOut)
async def confirm_reservation(
    reservation_id: uuid.UUID,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(*CAN_MANAGE)),
) -> ReservationOut:
    repo = ReservationRepository(session)
    async with session.begin():
        reservation = await repo.get(reservation_id)
        if reservation is None:
            raise HTTPException(status_code=404, detail="reservation not found")
        if reservation.status != ReservationStatus.PENDING.value:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_transition",
                    "message": f"cannot confirm a reservation in '{reservation.status}'",
                },
            )
        await repo.transition(reservation, new_status=ReservationStatus.CONFIRMED)
        room = await RoomRepository(session).get(reservation.room_id)
        reservation.room = room  # type: ignore[assignment]
        snapshot = _to_out(reservation)

    await publisher.publish(
        channel=Channels.RESERVATION_CONFIRMED,
        payload={"reservation_id": str(reservation_id)},
    )
    return snapshot


@router.post("/{reservation_id}/cancel", response_model=ReservationOut)
async def cancel_reservation(
    reservation_id: uuid.UUID,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(*CAN_MANAGE)),
) -> ReservationOut:
    repo = ReservationRepository(session)
    async with session.begin():
        reservation = await repo.get(reservation_id)
        if reservation is None:
            raise HTTPException(status_code=404, detail="reservation not found")
        if reservation.status not in (
            ReservationStatus.PENDING.value,
            ReservationStatus.CONFIRMED.value,
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_transition",
                    "message": f"cannot cancel a reservation in '{reservation.status}'",
                },
            )
        await repo.transition(reservation, new_status=ReservationStatus.CANCELLED)
        room = await RoomRepository(session).get(reservation.room_id)
        reservation.room = room  # type: ignore[assignment]
        snapshot = _to_out(reservation)

    await publisher.publish(
        channel=Channels.RESERVATION_CANCELLED,
        payload={"reservation_id": str(reservation_id)},
    )
    return snapshot


@router.post("/{reservation_id}/no-show", response_model=ReservationOut)
async def mark_no_show(
    reservation_id: uuid.UUID,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(*CAN_MANAGE)),
) -> ReservationOut:
    repo = ReservationRepository(session)
    async with session.begin():
        reservation = await repo.get(reservation_id)
        if reservation is None:
            raise HTTPException(status_code=404, detail="reservation not found")
        if reservation.status not in (
            ReservationStatus.PENDING.value,
            ReservationStatus.CONFIRMED.value,
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_transition",
                    "message": f"cannot mark a '{reservation.status}' reservation as no-show",
                },
            )
        await repo.transition(reservation, new_status=ReservationStatus.NO_SHOW)
        room = await RoomRepository(session).get(reservation.room_id)
        reservation.room = room  # type: ignore[assignment]
        snapshot = _to_out(reservation)

    await publisher.publish(
        channel=Channels.RESERVATION_NO_SHOW,
        payload={"reservation_id": str(reservation_id)},
    )
    return snapshot


@router.post("/{reservation_id}/check-in", response_model=GuestOut)
async def check_in_reservation(
    reservation_id: uuid.UUID,
    payload: ReservationCheckInRequest,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(*CAN_MANAGE)),
) -> GuestOut:
    """Materialise the reservation into an active Guest stay.

    Mirrors the walk-in `/guests/check-in` flow: locks the room, marks it
    occupied, creates the Guest row, then flips the reservation to
    CHECKED_IN with a back-reference to the new guest.
    """
    rooms = RoomRepository(session)
    guests = GuestRepository(session)
    repo = ReservationRepository(session)

    async with session.begin():
        reservation = await repo.get(reservation_id)
        if reservation is None:
            raise HTTPException(status_code=404, detail="reservation not found")
        if reservation.status not in (
            ReservationStatus.PENDING.value,
            ReservationStatus.CONFIRMED.value,
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_transition",
                    "message": (
                        f"reservation is '{reservation.status}', cannot check in"
                    ),
                },
            )

        room = await rooms.lock_specific_assignable(reservation.room_id)
        if room is None:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "room_not_available",
                    "message": (
                        "reserved room is not currently clean+available — "
                        "maintenance or housekeeping may be in progress"
                    ),
                },
            )
        await rooms.mark_occupied(room)

        # Hotel-day length: from now until the reservation's check-out date
        # at noon. Simpler than carrying booking time-of-day; matches the
        # billing's nights × rate model.
        checkout_dt = datetime.combine(
            reservation.check_out_date, time(12, 0), tzinfo=timezone.utc
        )
        guest = await guests.create(
            full_name=reservation.full_name,
            phone=reservation.phone,
            passport_number=reservation.passport_number,
            room_id=room.id,
            expected_checkout_at=checkout_dt,
            nightly_rate_locked_minor_units=reservation.nightly_rate_locked_minor_units,
            cleaning_preference=payload.cleaning_preference or "afternoon",
            cleaning_preference_note=payload.cleaning_preference_note,
        )
        await repo.transition(
            reservation,
            new_status=ReservationStatus.CHECKED_IN,
            guest_id=guest.id,
        )
        snapshot = GuestOut(
            id=str(guest.id),
            full_name=guest.full_name,
            phone=guest.phone,
            room_id=str(room.id),
            room_number=room.room_number,
            floor=room.floor,
            room_type=room.room_type,
            checked_in_at=guest.checked_in_at,
            expected_checkout_at=guest.expected_checkout_at,
            nightly_rate_locked_minor_units=guest.nightly_rate_locked_minor_units,
            do_not_disturb=guest.do_not_disturb,
            cleaning_preference=guest.cleaning_preference,
            cleaning_preference_note=guest.cleaning_preference_note,
        )

    await publisher.publish(
        channel=Channels.GUEST_CHECKED_IN,
        payload={
            "guest_id": snapshot.id,
            "room_id": snapshot.room_id,
            "room_number": snapshot.room_number,
            "floor": snapshot.floor,
            "room_type": snapshot.room_type,
            "full_name": snapshot.full_name,
            "checked_in_at": snapshot.checked_in_at.isoformat(),
        },
    )
    return snapshot
