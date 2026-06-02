"""Guest endpoints: check-in, check-out, and active list.

Check-in runs the room assignment algorithm under `SELECT … FOR UPDATE
SKIP LOCKED`. Check-out runs the billing algorithm, persists a `Bill`, and
fans out three events:

    bills.finalized   → ws-gateway (manager only)
    guests.checked_out → ws-gateway
    rooms.vacated      → housekeeping (enqueue) + ws-gateway

The room stays `status=available` but flips `cleanliness=dirty`, so the
assignment filter excludes it until housekeeping marks it clean again.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import PublisherDep, SessionDep, require_role
from src.api.schemas.billing import CheckOutResponse
from src.api.schemas.guest import CheckInRequest, DailyCount, GuestOut
from src.domain.enums import Cleanliness, RoomStatus, UserRole
from src.events.topics import Channels
from src.infra.repositories.bill_repository import BillRepository
from src.infra.repositories.guest_repository import GuestRepository
from src.infra.repositories.order_repository import OrderRepository
from src.infra.repositories.room_repository import RoomRepository
from src.services.billing import compute_bill
from src.services.room_assignment import (
    AssignmentRequest,
    NoRoomsAvailable,
    pick_room,
)

router = APIRouter(prefix="/guests", tags=["guests"])

CAN_CHECK_IN = (UserRole.MANAGER, UserRole.RECEPTION)


@router.get("/stats/daily", response_model=list[DailyCount])
async def daily_guest_stats(
    session: SessionDep,
    days: int = 30,
    _=Depends(require_role(*CAN_CHECK_IN)),
) -> list[DailyCount]:
    """Daily check-in counts over the last `days` days (dense — zero days
    included). Powers the dashboard's "guests over time" chart.

    Defined ABOVE `/{guest_id}/check-out` so FastAPI matches the literal
    path first; otherwise `stats` would be parsed as a guest id and fail
    validation.
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be 1..365")
    rows = await GuestRepository(session).daily_checkin_counts(days=days)
    return [DailyCount(date=d, count=n) for (d, n) in rows]


@router.get("", response_model=list[GuestOut])
async def list_active_guests(
    session: SessionDep,
    _=Depends(require_role(*CAN_CHECK_IN)),
) -> list[GuestOut]:
    guests = await GuestRepository(session).list_active()
    return [
        GuestOut(
            id=str(g.id),
            full_name=g.full_name,
            phone=g.phone,
            room_id=str(g.room_id),
            room_number=g.room.room_number,
            floor=g.room.floor,
            room_type=g.room.room_type,
            checked_in_at=g.checked_in_at,
            expected_checkout_at=g.expected_checkout_at,
            nightly_rate_locked_minor_units=g.nightly_rate_locked_minor_units,
        )
        for g in guests
    ]


@router.post("/check-in", response_model=GuestOut, status_code=status.HTTP_201_CREATED)
async def check_in(
    payload: CheckInRequest,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(*CAN_CHECK_IN)),
) -> GuestOut:
    rooms = RoomRepository(session)
    guests = GuestRepository(session)

    # Single transaction wraps:
    #   1. SELECT … FOR UPDATE SKIP LOCKED  (either a one-row lock by id
    #      or the algorithm shortlist)
    #   2. UPDATE room   SET status=occupied
    #   3. INSERT guest
    # Concurrent identical requests serialise on the first match they manage
    # to lock; the loser's SKIP LOCKED pushes it to the next candidate.
    try:
        async with session.begin():
            if payload.room_id is not None:
                # Direct assignment — receptionist clicked a specific room
                # card. Skip the algorithm.
                room = await rooms.lock_specific_assignable(payload.room_id)
                if room is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "room_not_available",
                            "room_id": str(payload.room_id),
                            "message": (
                                "selected room is no longer clean+available "
                                "(another booking may have taken it)"
                            ),
                        },
                    )
            else:
                assert payload.room_type is not None  # enforced by validator
                room = await pick_room(
                    AssignmentRequest(
                        room_type=payload.room_type,
                        floor_preference=payload.floor_preference,
                        proximity_preference=payload.proximity_preference,
                    ),
                    rooms,
                )
            await rooms.mark_occupied(room)
            expected_checkout = datetime.now(timezone.utc) + timedelta(days=payload.nights)
            guest = await guests.create(
                full_name=payload.full_name,
                phone=payload.phone,
                passport_number=payload.passport_number,
                room_id=room.id,
                expected_checkout_at=expected_checkout,
                nightly_rate_locked_minor_units=room.nightly_rate_minor_units,
            )
            # Snapshot values before the session closes — lazy attribute
            # access after commit triggers IO on an expired instance.
            guest_id = str(guest.id)
            room_id = str(room.id)
            room_number = room.room_number
            floor = room.floor
            room_type = room.room_type
            checked_in_at = guest.checked_in_at
            rate = guest.nightly_rate_locked_minor_units
    except NoRoomsAvailable as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "no_rooms_available",
                "room_type": exc.room_type.value,
                "message": "no clean room of the requested type is available",
            },
        ) from exc

    await publisher.publish(
        channel=Channels.GUEST_CHECKED_IN,
        payload={
            "guest_id": guest_id,
            "room_id": room_id,
            "room_number": room_number,
            "floor": floor,
            "room_type": room_type,
            "full_name": payload.full_name,
            "checked_in_at": checked_in_at.isoformat(),
        },
    )

    return GuestOut(
        id=guest_id,
        full_name=payload.full_name,
        phone=payload.phone,
        room_id=room_id,
        room_number=room_number,
        floor=floor,
        room_type=room_type,
        checked_in_at=checked_in_at,
        expected_checkout_at=expected_checkout,
        nightly_rate_locked_minor_units=rate,
    )


@router.post(
    "/{guest_id}/check-out",
    response_model=CheckOutResponse,
    status_code=status.HTTP_200_OK,
)
async def check_out(
    guest_id: uuid.UUID,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(*CAN_CHECK_IN)),
) -> CheckOutResponse:
    guests = GuestRepository(session)
    rooms = RoomRepository(session)
    bills = BillRepository(session)

    async with session.begin():
        guest = await guests.get(guest_id)
        if guest is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guest not found")
        if guest.checked_out_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "already_checked_out",
                    "message": "guest already checked out",
                    "checked_out_at": guest.checked_out_at.isoformat(),
                },
            )

        now = datetime.now(timezone.utc)
        # Bill at least one full night even for a same-day check-out — this is
        # the standard hotel rule and matches the brief's "early check-out"
        # edge case.
        elapsed_hours = (now - guest.checked_in_at).total_seconds() / 3600.0
        nights_stayed = max(1, math.ceil(elapsed_hours / 24.0))

        # Aggregate every delivered room-service order for this guest. Open
        # orders (not yet delivered) are *not* billed — staff can finish or
        # cancel them before the bill is finalised.
        delivered = await OrderRepository(session).list_delivered_for_guest(guest.id)
        order_charges = [o.total_minor_units for o in delivered]

        snapshot = compute_bill(
            nightly_rate_minor_units=guest.nightly_rate_locked_minor_units,
            nights=nights_stayed,
            room_service_charges=order_charges,
        )

        bill = await bills.create(guest_id=guest.id, room_id=guest.room_id, snapshot=snapshot)
        guest.checked_out_at = now

        room = await rooms.get(guest.room_id)
        # Status flips back to available (no guest), but cleanliness becomes
        # dirty — the assignment algorithm filters on `cleanliness=clean`,
        # so the room is not reassignable until housekeeping cleans it.
        room.status = RoomStatus.AVAILABLE.value
        room.cleanliness_status = Cleanliness.DIRTY.value

        # Snapshot before commit closes the session.
        bill_id = bill.id
        finalized_at = bill.finalized_at
        room_number = room.room_number
        floor = room.floor

    # Three events fan out post-commit. Order matters for the dashboard's
    # narrative: bill → guest → vacated.
    await publisher.publish(
        channel=Channels.BILL_FINALIZED,
        payload={
            "bill_id": str(bill_id),
            "guest_id": str(guest.id),
            "room_number": room_number,
            "total_minor_units": snapshot.total_minor_units,
            "finalized_at": finalized_at.isoformat(),
        },
    )
    await publisher.publish(
        channel=Channels.GUEST_CHECKED_OUT,
        payload={
            "guest_id": str(guest.id),
            "room_id": str(guest.room_id),
            "room_number": room_number,
            "checked_out_at": now.isoformat(),
            "bill_id": str(bill_id),
            "total_minor_units": snapshot.total_minor_units,
        },
    )
    await publisher.publish(
        channel=Channels.ROOM_VACATED,
        payload={
            "room_id": str(guest.room_id),
            "room_number": room_number,
            "floor": floor,
            "vacated_at": now.isoformat(),
        },
    )

    return CheckOutResponse(
        guest_id=guest.id,
        room_number=room_number,
        bill_id=bill_id,
        nights=snapshot.nights,
        nightly_rate_minor_units=snapshot.nightly_rate_minor_units,
        room_cost_minor_units=snapshot.room_cost_minor_units,
        room_service_charges_minor_units=snapshot.room_service_charges_minor_units,
        extras_minor_units=snapshot.extras_minor_units,
        discount_minor_units=snapshot.discount_minor_units,
        total_minor_units=snapshot.total_minor_units,
        finalized_at=finalized_at,
        checked_out_at=now,
    )
