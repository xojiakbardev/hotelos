"""Inbound event handlers for maintenance-service.

Subscribes to `users.*` events from auth-service to keep a local
technician projection. Maintenance never calls auth over HTTP, so this
projection is the only path for showing technician name+phone on the
manager dashboard and the guest portal.
"""

from __future__ import annotations

import logging
import uuid

from src.core.db import async_session_factory
from src.domain.enums import IssueStatus
from src.domain.models import Issue
from src.events.publisher import EventPublisher
from src.events.topics import Channels
from src.infra.repositories.technician_repository import TechnicianRepository

logger = logging.getLogger("maintenance-service.handlers")


# Set by main.py during startup so guest-portal-triggered handlers can
# publish the canonical follow-up event.
_publisher: EventPublisher | None = None


def set_publisher(publisher: EventPublisher) -> None:
    global _publisher
    _publisher = publisher


async def on_user_created(envelope: dict) -> None:
    payload = envelope.get("payload") or {}
    user_id = payload.get("user_id")
    phone = payload.get("phone")
    if not user_id or not phone:
        return
    async with async_session_factory() as session:
        async with session.begin():
            await TechnicianRepository(session).upsert(
                user_id=uuid.UUID(user_id),
                full_name=payload.get("full_name"),
                phone=phone,
                role=str(payload.get("role") or ""),
                is_active=bool(payload.get("is_active", True)),
            )
    logger.info("cached user id=%s phone=%s", user_id, phone)


async def on_user_updated(envelope: dict) -> None:
    # Same upsert semantics; events.created and events.updated are
    # interchangeable from our cache's point of view.
    await on_user_created(envelope)


async def on_user_deactivated(envelope: dict) -> None:
    payload = envelope.get("payload") or {}
    user_id = payload.get("user_id")
    if not user_id:
        return
    async with async_session_factory() as session:
        async with session.begin():
            await TechnicianRepository(session).deactivate(uuid.UUID(user_id))
    logger.info("deactivated cached user id=%s", user_id)


async def on_guest_portal_maintenance_requested(envelope: dict) -> None:
    """Materialise a guest-portal maintenance request as a real Issue
    row and emit the canonical maintenance.reported event so the manager
    dashboard, room status, and reception projection all see it.
    """
    payload = envelope.get("payload") or {}
    room_id = payload.get("room_id")
    if not room_id:
        return
    async with async_session_factory() as session:
        async with session.begin():
            issue = Issue(
                room_id=uuid.UUID(room_id),
                room_number=int(payload.get("room_number") or 0),
                floor=int(payload.get("floor") or 0),
                urgency=str(payload.get("urgency") or "normal"),
                description=str(payload.get("description") or "")[:500],
                status=IssueStatus.REPORTED.value,
                reported_by_user_id=uuid.UUID(payload["reported_by_user_id"]),
            )
            session.add(issue)
            await session.flush()
            issue_id = str(issue.id)
            reported_at = issue.reported_at

    if _publisher is not None:
        await _publisher.publish(
            channel=Channels.MAINTENANCE_REPORTED,
            payload={
                "issue_id": issue_id,
                "room_id": room_id,
                "room_number": payload.get("room_number"),
                "floor": payload.get("floor"),
                "urgency": str(payload.get("urgency") or "normal"),
                "description": payload.get("description"),
                "reported_by_user_id": payload.get("reported_by_user_id"),
                "reported_at": reported_at.isoformat(),
                "guest_id": payload.get("guest_id"),
            },
        )
    logger.info("materialised guest-portal maintenance request -> issue %s", issue_id)
