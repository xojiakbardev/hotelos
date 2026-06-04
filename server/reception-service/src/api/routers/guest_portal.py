"""Guest self-service portal endpoints.

Guests access these after check-in using credentials generated at check-in.
All endpoints require an active guest JWT (role=guest, valid guest_id+room_id).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import GuestContextDep, PublisherDep, SessionDep
from src.api.schemas.guest_portal import (
    GuestCleaningCreate,
    GuestCleaningOut,
    GuestDashboardOut,
    GuestMaintenanceCreate,
    GuestMaintenanceOut,
    GuestOrderCreate,
    GuestOrderOut,
)
from src.domain.models import CleaningRequest, Order
from src.events.topics import Channels
from src.infra.repositories.guest_repository import GuestRepository
from src.infra.repositories.order_repository import OrderRepository

router = APIRouter(prefix="/guest-portal", tags=["guest-portal"])


@router.get("/dashboard", response_model=GuestDashboardOut)
async def guest_dashboard(
    session: SessionDep,
    guest: GuestContextDep,
) -> GuestDashboardOut:
    """Aggregated dashboard: all orders, maintenance requests, cleaning requests."""
    from sqlalchemy import select
    from src.domain.models import CleaningRequest

    guest_uuid = uuid.UUID(guest.guest_id)

    # Orders
    orders_repo = OrderRepository(session)
    orders = await orders_repo.list_for_guest(guest_uuid)
    orders_out = [
        GuestOrderOut(
            id=o.id, status=o.status, items=o.items,
            total_minor_units=o.total_minor_units,
            received_at=o.received_at, preparing_at=o.preparing_at,
            delivering_at=o.delivering_at, delivered_at=o.delivered_at,
        )
        for o in orders
    ]

    # Maintenance requests — fetch from local projection or just show guest's
    # For now we query reception's knowledge of maintenance via events stored locally
    # Actually maintenance is a separate service. Guest sees status via WS events.
    # We'll return empty for now and rely on WS for real-time.
    # TODO: If we want history, reception could keep a local projection.
    maintenance_out: list[GuestMaintenanceOut] = []

    # Cleaning requests
    room_uuid = uuid.UUID(guest.room_id)
    stmt = (
        select(CleaningRequest)
        .where(CleaningRequest.guest_id == guest_uuid)
        .order_by(CleaningRequest.requested_at.desc())
    )
    cleaning_rows = (await session.execute(stmt)).scalars().all()
    cleaning_out = [
        GuestCleaningOut(
            id=cr.id, priority=cr.priority, preferred_time=cr.preferred_time,
            note=cr.note, status=cr.status,
            requested_at=cr.requested_at, completed_at=cr.completed_at,
        )
        for cr in cleaning_rows
    ]

    # Get guest name from guest record
    guest_record = await GuestRepository(session).get(guest_uuid)
    guest_name = guest_record.full_name if guest_record else "Mehmon"

    return GuestDashboardOut(
        guest_name=guest_name,
        room_number=guest.room_number,
        floor=0,  # will be filled from room data
        orders=orders_out,
        maintenance_requests=maintenance_out,
        cleaning_requests=cleaning_out,
    )


@router.post("/orders", response_model=GuestOrderOut, status_code=status.HTTP_201_CREATED)
async def create_guest_order(
    payload: GuestOrderCreate,
    session: SessionDep,
    publisher: PublisherDep,
    guest: GuestContextDep,
) -> GuestOrderOut:
    """Guest submits a food order."""
    guest_uuid = uuid.UUID(guest.guest_id)
    room_uuid = uuid.UUID(guest.room_id)

    # Validate guest is still checked in
    guest_record = await GuestRepository(session).get(guest_uuid)
    if guest_record is None or guest_record.checked_out_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not checked in")

    # Calculate total
    total = sum(item.get("price_minor_units", 0) * item.get("qty", 1) for item in payload.items)

    order = Order(
        guest_id=guest_uuid,
        room_id=room_uuid,
        room_number=guest.room_number,
        floor=guest_record.room.floor,
        status="received",
        items=payload.items,
        total_minor_units=total,
        taken_by_user_id=uuid.UUID(guest.auth_user_id),
    )
    session.add(order)
    await session.flush()
    order_id = order.id
    received_at = order.received_at
    await session.commit()

    await publisher.publish(
        channel=Channels.ORDER_RECEIVED,
        payload={
            "order_id": str(order_id),
            "guest_id": guest.guest_id,
            "room_id": guest.room_id,
            "room_number": guest.room_number,
            "items": payload.items,
            "total_minor_units": total,
            "received_at": received_at.isoformat(),
        },
    )

    return GuestOrderOut(
        id=order_id, status="received", items=payload.items,
        total_minor_units=total, received_at=received_at,
    )


@router.post("/maintenance", status_code=status.HTTP_201_CREATED)
async def create_guest_maintenance(
    payload: GuestMaintenanceCreate,
    session: SessionDep,
    publisher: PublisherDep,
    guest: GuestContextDep,
) -> dict:
    """Guest reports a maintenance issue. Published to maintenance-service via broker."""
    guest_uuid = uuid.UUID(guest.guest_id)
    guest_record = await GuestRepository(session).get(guest_uuid)
    if guest_record is None or guest_record.checked_out_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not checked in")

    await publisher.publish(
        channel=Channels.MAINTENANCE_REPORTED,
        payload={
            "room_id": guest.room_id,
            "room_number": guest.room_number,
            "floor": guest_record.room.floor,
            "urgency": "normal",
            "description": payload.description,
            "reported_by_user_id": guest.auth_user_id,
        },
    )

    return {"status": "reported", "message": "Muammo xabar qilindi"}


@router.post("/cleaning", response_model=GuestCleaningOut, status_code=status.HTTP_201_CREATED)
async def create_guest_cleaning(
    payload: GuestCleaningCreate,
    session: SessionDep,
    publisher: PublisherDep,
    guest: GuestContextDep,
) -> GuestCleaningOut:
    """Guest requests room cleaning."""
    guest_uuid = uuid.UUID(guest.guest_id)
    guest_record = await GuestRepository(session).get(guest_uuid)
    if guest_record is None or guest_record.checked_out_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not checked in")

    if guest_record.do_not_disturb:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bezovta qilmaslik rejimi yoqilgan. Avval uni o'chiring.",
        )

    cr = CleaningRequest(
        guest_id=guest_uuid,
        room_id=uuid.UUID(guest.room_id),
        room_number=guest.room_number,
        floor=guest_record.room.floor,
        priority=payload.priority,
        preferred_time=payload.preferred_time,
        note=payload.note,
        status="pending",
    )
    session.add(cr)
    await session.flush()
    cr_id = cr.id
    requested_at = cr.requested_at
    await session.commit()

    await publisher.publish(
        channel=Channels.ROOM_CLEANING_REQUESTED,
        payload={
            "room_id": guest.room_id,
            "room_number": guest.room_number,
            "floor": guest_record.room.floor,
            "priority": payload.priority,
            "preferred_time": payload.preferred_time,
            "note": payload.note,
            "guest_id": guest.guest_id,
        },
    )

    return GuestCleaningOut(
        id=cr_id, priority=payload.priority,
        preferred_time=payload.preferred_time, note=payload.note,
        status="pending", requested_at=requested_at,
    )
