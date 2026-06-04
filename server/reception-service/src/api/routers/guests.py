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

from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import PublisherDep, SessionDep, require_role
from src.api.schemas.billing import CheckOutResponse
from src.api.schemas.guest import (
    CheckInRequest,
    CheckInResponse,
    CleaningPreferenceRequest,
    DailyCount,
    DNDRequest,
    GuestHistoryOut,
    GuestOut,
    StaySummary,
)
from src.domain.enums import Cleanliness, RoomStatus, UserRole
from src.events.topics import Channels
from src.infra.repositories.bill_repository import BillRepository
from src.infra.repositories.guest_repository import GuestRepository
from src.infra.repositories.order_repository import OrderRepository
from src.infra.repositories.room_repository import RoomRepository
from src.services.billing import compute_bill
from src.services.credential_generator import generate_guest_pin, hash_pin
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
            do_not_disturb=g.do_not_disturb,
            cleaning_preference=g.cleaning_preference,
            cleaning_preference_note=g.cleaning_preference_note,
        )
        for g in guests
    ]


@router.get("/history/by-phone/{phone}", response_model=GuestHistoryOut)
async def guest_history(
    phone: str,
    session: SessionDep,
    _=Depends(require_role(*CAN_CHECK_IN)),
) -> GuestHistoryOut:
    """All historical stays + loyalty aggregate for a phone number.

    Phone is used as the natural key because the system has no separate
    guest registration step — each stay creates a fresh Guest row, but
    repeat visitors call back on the same number.

    Declared above `/{guest_id}` so FastAPI matches the literal prefix
    first; otherwise "history" would try to validate as a UUID.
    """
    normalised = unquote(phone).strip()
    stays = await GuestRepository(session).list_by_phone(normalised)
    if not stays:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no stays for phone")

    stay_rows: list[StaySummary] = []
    total_nights = 0
    total_spent = 0
    for g in stays:
        # A stay's "nights" comes from the finalized bill if available,
        # otherwise falls back to elapsed days (still-active stay).
        bill = g.bills[0] if g.bills else None
        if bill is not None:
            nights = bill.nights
            total_spent += bill.total_minor_units
        else:
            elapsed = (
                (g.checked_out_at or datetime.now(timezone.utc)) - g.checked_in_at
            ).total_seconds() / 86400.0
            nights = max(1, math.ceil(elapsed))
        total_nights += nights
        stay_rows.append(
            StaySummary(
                guest_id=str(g.id),
                room_number=g.room.room_number,
                floor=g.room.floor,
                checked_in_at=g.checked_in_at,
                checked_out_at=g.checked_out_at,
                nights=nights,
                total_minor_units=bill.total_minor_units if bill else None,
                bill_id=str(bill.id) if bill else None,
            )
        )

    newest = stays[0]
    return GuestHistoryOut(
        phone=normalised,
        full_name=newest.full_name,
        stays=stay_rows,
        total_stays=len(stays),
        total_nights=total_nights,
        total_spent_minor_units=total_spent,
        last_checked_in_at=newest.checked_in_at,
        repeat_visitor=len(stays) > 1,
    )


@router.get("/{guest_id}", response_model=GuestOut)
async def get_guest(
    guest_id: uuid.UUID,
    session: SessionDep,
    _=Depends(require_role(*CAN_CHECK_IN)),
) -> GuestOut:
    guest = await GuestRepository(session).get(guest_id)
    if guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guest not found")
    return GuestOut(
        id=str(guest.id),
        full_name=guest.full_name,
        phone=guest.phone,
        room_id=str(guest.room_id),
        room_number=guest.room.room_number,
        floor=guest.room.floor,
        room_type=guest.room.room_type,
        checked_in_at=guest.checked_in_at,
        expected_checkout_at=guest.expected_checkout_at,
        nightly_rate_locked_minor_units=guest.nightly_rate_locked_minor_units,
        do_not_disturb=guest.do_not_disturb,
        cleaning_preference=guest.cleaning_preference,
        cleaning_preference_note=guest.cleaning_preference_note,
    )


@router.post("/check-in", response_model=CheckInResponse, status_code=status.HTTP_201_CREATED)
async def check_in(
    payload: CheckInRequest,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(*CAN_CHECK_IN)),
) -> CheckInResponse:
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

            # Generate guest self-service credentials
            auth_user_id = uuid.uuid4()
            guest_pin = generate_guest_pin()
            pin_hash = hash_pin(guest_pin)

            guest = await guests.create(
                full_name=payload.full_name,
                phone=payload.phone,
                passport_number=payload.passport_number,
                room_id=room.id,
                expected_checkout_at=expected_checkout,
                nightly_rate_locked_minor_units=room.nightly_rate_minor_units,
                cleaning_preference=payload.cleaning_preference.value,
                cleaning_preference_note=payload.cleaning_preference_note,
                auth_user_id=auth_user_id,
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
            dnd = guest.do_not_disturb
            cleaning_pref = guest.cleaning_preference
            cleaning_pref_note = guest.cleaning_preference_note
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

    # Publish credential event so auth-service creates the guest user
    await publisher.publish(
        channel=Channels.GUEST_CREDENTIAL_CREATED,
        payload={
            "auth_user_id": str(auth_user_id),
            "phone": payload.phone,
            "password_hash": pin_hash,
            "full_name": payload.full_name,
            "guest_id": guest_id,
            "room_id": room_id,
            "room_number": room_number,
        },
    )

    return CheckInResponse(
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
        do_not_disturb=dnd,
        cleaning_preference=cleaning_pref,
        cleaning_preference_note=cleaning_pref_note,
        auth_user_id=str(auth_user_id),
        guest_pin=guest_pin,
        guest_login=payload.phone,
    )


@router.put("/{guest_id}/dnd", response_model=GuestOut)
async def set_do_not_disturb(
    guest_id: uuid.UUID,
    payload: DNDRequest,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(*CAN_CHECK_IN)),
) -> GuestOut:
    """Toggle the guest's DND flag. Only valid for guests who are still
    checked in — flipping it on a checked-out guest is a no-op error."""
    repo = GuestRepository(session)
    async with session.begin():
        guest = await repo.get(guest_id)
        if guest is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guest not found")
        if guest.checked_out_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "not_checked_in", "message": "guest already checked out"},
            )
        await repo.set_dnd(guest, payload.do_not_disturb)
        snapshot = GuestOut(
            id=str(guest.id),
            full_name=guest.full_name,
            phone=guest.phone,
            room_id=str(guest.room_id),
            room_number=guest.room.room_number,
            floor=guest.room.floor,
            room_type=guest.room.room_type,
            checked_in_at=guest.checked_in_at,
            expected_checkout_at=guest.expected_checkout_at,
            nightly_rate_locked_minor_units=guest.nightly_rate_locked_minor_units,
            do_not_disturb=guest.do_not_disturb,
            cleaning_preference=guest.cleaning_preference,
            cleaning_preference_note=guest.cleaning_preference_note,
        )

    await publisher.publish(
        channel=Channels.GUEST_DND_CHANGED,
        payload={
            "guest_id": snapshot.id,
            "room_id": snapshot.room_id,
            "room_number": snapshot.room_number,
            "do_not_disturb": snapshot.do_not_disturb,
        },
    )
    return snapshot


@router.put("/{guest_id}/cleaning-preference", response_model=GuestOut)
async def set_cleaning_preference(
    guest_id: uuid.UUID,
    payload: CleaningPreferenceRequest,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(*CAN_CHECK_IN)),
) -> GuestOut:
    repo = GuestRepository(session)
    async with session.begin():
        guest = await repo.get(guest_id)
        if guest is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guest not found")
        if guest.checked_out_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "not_checked_in", "message": "guest already checked out"},
            )
        await repo.set_cleaning_preference(
            guest,
            preference=payload.cleaning_preference.value,
            note=payload.cleaning_preference_note,
        )
        snapshot = GuestOut(
            id=str(guest.id),
            full_name=guest.full_name,
            phone=guest.phone,
            room_id=str(guest.room_id),
            room_number=guest.room.room_number,
            floor=guest.room.floor,
            room_type=guest.room.room_type,
            checked_in_at=guest.checked_in_at,
            expected_checkout_at=guest.expected_checkout_at,
            nightly_rate_locked_minor_units=guest.nightly_rate_locked_minor_units,
            do_not_disturb=guest.do_not_disturb,
            cleaning_preference=guest.cleaning_preference,
            cleaning_preference_note=guest.cleaning_preference_note,
        )

    await publisher.publish(
        channel=Channels.GUEST_PREFERENCES_CHANGED,
        payload={
            "guest_id": snapshot.id,
            "room_id": snapshot.room_id,
            "room_number": snapshot.room_number,
            "cleaning_preference": snapshot.cleaning_preference,
            "cleaning_preference_note": snapshot.cleaning_preference_note,
        },
    )
    return snapshot


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
        orders_repo = OrderRepository(session)
        delivered = await orders_repo.list_delivered_for_guest(guest.id)
        order_charges = [o.total_minor_units for o in delivered]

        snapshot = compute_bill(
            nightly_rate_minor_units=guest.nightly_rate_locked_minor_units,
            nights=nights_stayed,
            room_service_charges=order_charges,
        )

        bill = await bills.create(guest_id=guest.id, room_id=guest.room_id, snapshot=snapshot)
        # Stamp each delivered order as billed inside the same transaction —
        # an outage between bill INSERT and this UPDATE would otherwise leave
        # the orders eligible for a second invoice.
        await orders_repo.mark_billed(delivered)
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

    # Deactivate guest self-service credentials
    if guest.auth_user_id:
        await publisher.publish(
            channel=Channels.GUEST_CREDENTIAL_DEACTIVATED,
            payload={
                "auth_user_id": str(guest.auth_user_id),
                "guest_id": str(guest.id),
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


@router.post("/{guest_id}/reset-pin")
async def reset_guest_pin(
    guest_id: uuid.UUID,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(*CAN_CHECK_IN)),
) -> dict:
    """Generate a new PIN for a guest who lost their credentials."""
    guest = await GuestRepository(session).get(guest_id)
    if guest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guest not found")
    if guest.checked_out_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot reset PIN for checked-out guest",
        )
    if not guest.auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="guest has no self-service credentials",
        )

    new_pin = generate_guest_pin()
    pin_hash = hash_pin(new_pin)

    await publisher.publish(
        channel=Channels.GUEST_CREDENTIAL_UPDATED,
        payload={
            "auth_user_id": str(guest.auth_user_id),
            "password_hash": pin_hash,
            "guest_id": str(guest.id),
        },
    )

    return {"new_pin": new_pin, "guest_login": guest.phone}
