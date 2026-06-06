"""Room-service order endpoints.

Reception owns the lifecycle. The room-service microservice receives
events and maintains its own projection for the kitchen view.

  POST /orders                        create new order (status=received)
  POST /orders/{id}/advance           move to next status
  GET  /orders                        all open orders (kitchen-side view)
  GET  /orders/by-guest/{guest_id}    everything for one guest
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import (
    CurrentUserDep,
    PublisherDep,
    SessionDep,
    require_role,
)
from src.api.schemas.order import OrderCreate, OrderOut
from src.domain.enums import OrderStatus, UserRole
from src.events.topics import Channels
from src.infra.repositories.guest_repository import GuestRepository
from src.infra.repositories.order_repository import OrderRepository
from src.services.order_lifecycle import IllegalTransition, next_status

router = APIRouter(prefix="/orders", tags=["orders"])

CAN_WORK = (UserRole.MANAGER, UserRole.RECEPTION, UserRole.KITCHEN)


def _status_to_channel(s: OrderStatus) -> str:
    return {
        OrderStatus.RECEIVED: Channels.ORDER_RECEIVED,
        OrderStatus.PREPARING: Channels.ORDER_PREPARING,
        OrderStatus.DELIVERING: Channels.ORDER_DELIVERING,
        OrderStatus.DELIVERED: Channels.ORDER_DELIVERED,
    }[s]


@router.get("", response_model=list[OrderOut])
async def list_open_orders(
    session: SessionDep,
    _=Depends(require_role(*CAN_WORK)),
) -> list[OrderOut]:
    rows = await OrderRepository(session).list_open()
    return [OrderOut.model_validate(o, from_attributes=True) for o in rows]


@router.get("/history", response_model=list[OrderOut])
async def list_delivered_orders(
    session: SessionDep,
    _=Depends(require_role(*CAN_WORK)),
) -> list[OrderOut]:
    """Recently delivered orders (last 50)."""
    rows = await OrderRepository(session).list_delivered_recent()
    return [OrderOut.model_validate(o, from_attributes=True) for o in rows]


@router.get("/by-guest/{guest_id}", response_model=list[OrderOut])
async def list_for_guest(
    guest_id: uuid.UUID,
    session: SessionDep,
    _=Depends(require_role(*CAN_WORK)),
) -> list[OrderOut]:
    rows = await OrderRepository(session).list_for_guest(guest_id)
    return [OrderOut.model_validate(o, from_attributes=True) for o in rows]


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    session: SessionDep,
    publisher: PublisherDep,
    user: CurrentUserDep,
    _=Depends(require_role(*CAN_WORK)),
) -> OrderOut:
    guests = GuestRepository(session)
    orders = OrderRepository(session)

    async with session.begin():
        guest = await guests.get(payload.guest_id)
        if guest is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="guest not found")
        if guest.checked_out_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "guest_checked_out",
                    "message": "cannot create an order for a checked-out guest",
                },
            )

        items_serializable = [i.model_dump() for i in payload.items]
        total = sum(i.qty * i.price_minor_units for i in payload.items)

        order = await orders.create(
            guest_id=guest.id,
            room_id=guest.room_id,
            room_number=guest.room.room_number,
            floor=guest.room.floor,
            items=items_serializable,
            total_minor_units=total,
            taken_by_user_id=uuid.UUID(user.id),
        )
        snapshot = OrderOut.model_validate(order, from_attributes=True)

    await publisher.publish(
        channel=Channels.ORDER_RECEIVED,
        payload={
            "order_id": str(snapshot.id),
            "guest_id": str(snapshot.guest_id),
            "room_id": str(snapshot.room_id),
            "room_number": snapshot.room_number,
            "floor": snapshot.floor,
            "items": snapshot.items,
            "total_minor_units": snapshot.total_minor_units,
            "taken_by_user_id": user.id,
            "received_at": snapshot.received_at.isoformat(),
        },
    )
    return snapshot


@router.post("/{order_id}/advance", response_model=OrderOut)
async def advance(
    order_id: uuid.UUID,
    session: SessionDep,
    publisher: PublisherDep,
    user: CurrentUserDep,
    _=Depends(require_role(*CAN_WORK)),
) -> OrderOut:
    orders = OrderRepository(session)
    async with session.begin():
        order = await orders.get(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order not found")
        try:
            nxt = next_status(OrderStatus(order.status))
        except IllegalTransition as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "terminal_state",
                    "message": str(exc),
                    "current_status": order.status,
                },
            ) from exc
        await orders.set_status(order, nxt)
        snapshot = OrderOut.model_validate(order, from_attributes=True)

    await publisher.publish(
        channel=_status_to_channel(nxt),
        payload={
            "order_id": str(snapshot.id),
            "guest_id": str(snapshot.guest_id),
            "room_number": snapshot.room_number,
            "floor": snapshot.floor,
            "new_status": nxt.value,
            "transitioned_at": (
                snapshot.preparing_at
                or snapshot.delivering_at
                or snapshot.delivered_at
                or snapshot.received_at
            ).isoformat(),
            "advanced_by_user_id": user.id,
        },
    )
    return snapshot
