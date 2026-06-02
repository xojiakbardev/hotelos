"""Manager-only staff CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import SessionDep, require_role
from src.api.schemas.user import UserCreate, UserOut
from src.core.security.hash import hash_password
from src.domain.enums import UserRole
from src.infra.repositories.permission_repository import PermissionRepository
from src.infra.repositories.user_repository import UserRepository

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
    return UserOut(
        id=str(user.id),
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )
