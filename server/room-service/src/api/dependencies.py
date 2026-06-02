"""Reusable FastAPI dependencies."""

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
    id: str
    phone: str
    role: UserRole


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
    return CurrentUser(id=claims["sub"], phone=claims.get("phone", ""), role=role)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_role(*allowed: UserRole) -> Callable[[CurrentUser], CurrentUser]:
    async def _guard(user: CurrentUserDep) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return _guard


async def get_publisher(request: Request) -> EventPublisher:
    return request.app.state.publisher


PublisherDep = Annotated[EventPublisher, Depends(get_publisher)]
