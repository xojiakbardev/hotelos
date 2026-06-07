"""Manager-only staff CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.dependencies import PublisherDep, SessionDep, require_role
from src.api.schemas.user import UserCreate, UserOut, UserUpdate
from src.core.security.hash import hash_password
from src.domain.enums import UserRole
from src.events.topics import Channels
from src.infra.repositories.permission_repository import PermissionRepository
from src.infra.repositories.user_repository import UserRepository


def _user_event_payload(user) -> dict:
    return {
        "user_id": str(user.id),
        "phone": user.phone,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_active": user.is_active,
    }

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    session: SessionDep,
    role: UserRole | None = None,
    _=Depends(require_role(UserRole.MANAGER)),
) -> list[UserOut]:
    users = await UserRepository(session).list_active(role=role)
    return [
        UserOut(
            id=str(u.id), phone=u.phone, full_name=u.full_name, role=u.role, is_active=u.is_active
        )
        for u in users
    ]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(UserRole.MANAGER)),
) -> UserOut:
    repo = UserRepository(session)
    if await repo.get_by_phone(payload.phone) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="phone already registered"
        )
    user = await repo.create(
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        full_name=payload.full_name,
    )
    await PermissionRepository(session).create_default_entries_for_user(user.id, payload.role)
    await session.commit()
    await publisher.publish(channel=Channels.USER_CREATED, payload=_user_event_payload(user))
    return UserOut(
        id=str(user.id),
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


import uuid


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(UserRole.MANAGER)),
) -> UserOut:
    """Update a staff user's name, role, password, or active status."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    async with session.begin():
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.role is not None:
            user.role = payload.role
        if payload.password is not None:
            user.password_hash = hash_password(payload.password)
        if payload.is_active is not None:
            user.is_active = payload.is_active

    await publisher.publish(channel=Channels.USER_UPDATED, payload=_user_event_payload(user))
    return UserOut(
        id=str(user.id),
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    session: SessionDep,
    publisher: PublisherDep,
    _=Depends(require_role(UserRole.MANAGER)),
):
    """Soft-delete (deactivate) a staff user."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    if user.role == UserRole.MANAGER:
        managers = await repo.list_active(role=UserRole.MANAGER)
        if len(managers) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="cannot deactivate the last manager",
            )
    async with session.begin():
        user.is_active = False
    await publisher.publish(channel=Channels.USER_DEACTIVATED, payload=_user_event_payload(user))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
