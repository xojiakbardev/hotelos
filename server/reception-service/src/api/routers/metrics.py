"""Dashboard aggregation endpoint.

A single GET that rolls up the metrics the manager wants on the home
screen: room occupancy, today's + 7-day revenue, active guests, open
room-service orders. Everything else (cleaning queue, maintenance) lives
on those services and is already counted there.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from src.api.dependencies import SessionDep, require_role
from src.domain.enums import OrderStatus, RoomStatus, UserRole
from src.domain.models import Guest, Order, Room
from src.infra.repositories.bill_repository import BillRepository

router = APIRouter(prefix="/metrics", tags=["metrics"])

CAN_VIEW = (UserRole.MANAGER, UserRole.RECEPTION)


class DashboardMetrics(BaseModel):
    rooms_total: int
    rooms_occupied: int
    rooms_available_clean: int
    occupancy_rate: float  # 0.0 — 1.0
    active_guests: int
    open_orders: int
    revenue_today_minor_units: int
    revenue_week_minor_units: int


@router.get("/dashboard", response_model=DashboardMetrics)
async def dashboard_metrics(
    session: SessionDep,
    _=Depends(require_role(*CAN_VIEW)),
) -> DashboardMetrics:
    now = datetime.now(timezone.utc)
    # Start of today in UTC. Hotel-local TZ would be nicer but the brief
    # only requires UTC consistency, and Postgres is in UTC inside Docker.
    today_start = datetime.combine(now.date(), time(0, 0), tzinfo=timezone.utc)
    week_start = today_start - timedelta(days=6)

    total_rooms = int(
        (await session.execute(select(func.count(Room.id)))).scalar_one()
    )
    occupied = int(
        (
            await session.execute(
                select(func.count(Room.id)).where(Room.status == RoomStatus.OCCUPIED.value)
            )
        ).scalar_one()
    )
    available_clean = int(
        (
            await session.execute(
                select(func.count(Room.id)).where(
                    Room.status == RoomStatus.AVAILABLE.value,
                    Room.cleanliness_status == "clean",
                )
            )
        ).scalar_one()
    )
    active_guests = int(
        (
            await session.execute(
                select(func.count(Guest.id)).where(Guest.checked_out_at.is_(None))
            )
        ).scalar_one()
    )
    open_orders = int(
        (
            await session.execute(
                select(func.count(Order.id)).where(Order.status != OrderStatus.DELIVERED.value)
            )
        ).scalar_one()
    )

    bills = BillRepository(session)
    revenue_today = await bills.revenue_since(today_start)
    revenue_week = await bills.revenue_since(week_start)

    occupancy_rate = (occupied / total_rooms) if total_rooms else 0.0

    return DashboardMetrics(
        rooms_total=total_rooms,
        rooms_occupied=occupied,
        rooms_available_clean=available_clean,
        occupancy_rate=round(occupancy_rate, 4),
        active_guests=active_guests,
        open_orders=open_orders,
        revenue_today_minor_units=revenue_today,
        revenue_week_minor_units=revenue_week,
    )
