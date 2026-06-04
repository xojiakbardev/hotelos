"""Inbound event handlers for auth-service.

Handles guest credential lifecycle events published by reception-service.
Each handler manages its own DB session (runs outside FastAPI request scope).
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select

from src.core.db import async_session_factory
from src.domain.enums import UserRole
from src.domain.models import User, UserSettings

logger = logging.getLogger("auth-service.handlers")


async def on_guest_credential_created(envelope: dict) -> None:
    """Reception checked in a guest and generated credentials.

    Upsert: if a user with same phone + guest role exists, update it.
    Otherwise create a new user record.
    """
    payload = envelope.get("payload") or {}
    phone = payload.get("phone")
    password_hash = payload.get("password_hash")
    auth_user_id = payload.get("auth_user_id")
    if not phone or not password_hash or not auth_user_id:
        logger.warning("guest.credential_created missing required fields")
        return

    guest_id = payload.get("guest_id")
    room_id = payload.get("room_id")
    room_number = payload.get("room_number")
    full_name = payload.get("full_name")

    async with async_session_factory() as session:
        async with session.begin():
            # Check if user already exists (repeat guest with same phone)
            stmt = select(User).where(
                User.phone == phone, User.role == UserRole.GUEST
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if existing:
                existing.password_hash = password_hash
                existing.is_active = True
                existing.must_change_password = True
                existing.guest_id = uuid.UUID(guest_id) if guest_id else None
                existing.room_id = uuid.UUID(room_id) if room_id else None
                existing.room_number = room_number
                existing.full_name = full_name
                logger.info("updated guest credential for phone=%s", phone)
            else:
                user = User(
                    id=uuid.UUID(auth_user_id),
                    phone=phone,
                    password_hash=password_hash,
                    role=UserRole.GUEST,
                    full_name=full_name,
                    is_active=True,
                    must_change_password=True,
                    guest_id=uuid.UUID(guest_id) if guest_id else None,
                    room_id=uuid.UUID(room_id) if room_id else None,
                    room_number=room_number,
                )
                user.settings = UserSettings(preferred_locale="uz", extra={})
                session.add(user)
                logger.info("created guest user id=%s phone=%s", auth_user_id, phone)


async def on_guest_credential_deactivated(envelope: dict) -> None:
    """Guest checked out — deactivate their auth credential."""
    payload = envelope.get("payload") or {}
    auth_user_id = payload.get("auth_user_id")
    if not auth_user_id:
        return

    async with async_session_factory() as session:
        async with session.begin():
            user = await session.get(User, uuid.UUID(auth_user_id))
            if user and user.is_active:
                user.is_active = False
                logger.info("deactivated guest user id=%s", auth_user_id)


async def on_guest_credential_updated(envelope: dict) -> None:
    """PIN was reset by reception — update the password hash."""
    payload = envelope.get("payload") or {}
    auth_user_id = payload.get("auth_user_id")
    password_hash = payload.get("password_hash")
    if not auth_user_id or not password_hash:
        return

    async with async_session_factory() as session:
        async with session.begin():
            user = await session.get(User, uuid.UUID(auth_user_id))
            if user:
                user.password_hash = password_hash
                logger.info("updated PIN for guest user id=%s", auth_user_id)
