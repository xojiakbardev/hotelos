"""Reusable FastAPI dependencies.

Three things every protected endpoint needs:
  1. A database session (scoped per request, auto-rollbacks on exception).
  2. The current user, derived from the bearer token.
  3. A role guard factory for endpoint-level authorisation.

Plus one for the event publisher held in app.state by the lifespan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_session
from src.core.security.jwt import decode_access_token
from src.domain.enums import UserRole
from src.events.publisher import EventPublisher

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@dataclass(slots=True, frozen=True)
class CurrentUser:
    """Lightweight view of the authenticated caller. We don't load the User
    row from auth-service's database — the JWT itself carries everything
    reception needs (id, phone, role)."""

    id: str
    phone: str
    role: UserRole
    guest_id: str | None = None
    room_id: str | None = None
    room_number: int | None = None


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> CurrentUser:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing token")
    claims = decode_access_token(token)
    try:
        role = UserRole(claims["role"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid role claim"
        ) from exc
    return CurrentUser(
        id=claims["sub"],
        phone=claims.get("phone", ""),
        role=role,
        guest_id=claims.get("guest_id"),
        room_id=claims.get("room_id"),
        room_number=claims.get("room_number"),
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_role(*allowed: UserRole) -> Callable[[CurrentUser], CurrentUser]:
    """Endpoint guard. Usage:

        @router.post("/check-in")
        async def check_in(_=Depends(require_role(UserRole.RECEPTION, UserRole.MANAGER))): ...
    """

    async def _guard(user: CurrentUserDep) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return _guard


async def get_publisher(request: Request) -> EventPublisher:
    """Returns the singleton EventPublisher created by the lifespan."""
    return request.app.state.publisher


PublisherDep = Annotated[EventPublisher, Depends(get_publisher)]


@dataclass(slots=True, frozen=True)
class GuestContext:
    """Authenticated guest with confirmed active stay."""
    auth_user_id: str
    guest_id: str
    room_id: str
    room_number: int
    phone: str


async def require_active_guest(user: CurrentUserDep) -> GuestContext:
    """Dependency that validates the caller is a guest with an active stay."""
    if user.role != UserRole.GUEST:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="guest role required")
    if not user.guest_id or not user.room_id or user.room_number is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incomplete guest token — please log in again",
        )
    return GuestContext(
        auth_user_id=user.id,
        guest_id=user.guest_id,
        room_id=user.room_id,
        room_number=user.room_number,
        phone=user.phone,
    )


GuestContextDep = Annotated[GuestContext, Depends(require_active_guest)]
