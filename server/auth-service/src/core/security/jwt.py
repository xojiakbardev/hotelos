"""JWT issue + decode. The same shape every service expects."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from src.core.config import settings
from src.core.constants import JWT_CLAIM_GUEST_ID, JWT_CLAIM_PHONE, JWT_CLAIM_ROLE, JWT_CLAIM_ROOM_ID, JWT_CLAIM_ROOM_NUMBER, JWT_CLAIM_SUB


class InvalidTokenError(Exception):
    pass


def create_access_token(
    *,
    user_id: str,
    phone: str,
    role: str,
    guest_id: str | None = None,
    room_id: str | None = None,
    room_number: int | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    claims: dict[str, Any] = {
        JWT_CLAIM_SUB: user_id,
        JWT_CLAIM_PHONE: phone,
        JWT_CLAIM_ROLE: role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if role == "guest":
        if guest_id:
            claims[JWT_CLAIM_GUEST_ID] = guest_id
        if room_id:
            claims[JWT_CLAIM_ROOM_ID] = room_id
        if room_number is not None:
            claims[JWT_CLAIM_ROOM_NUMBER] = room_number
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
