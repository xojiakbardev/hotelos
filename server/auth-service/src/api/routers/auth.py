"""Public auth endpoints: POST /login, GET /me."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import CurrentUser, SessionDep
from src.api.schemas.auth import LoginRequest, MeResponse, TokenResponse
from src.infra.repositories.user_repository import UserRepository
from src.services.auth_service import AuthService

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    from src.services.audit import write_audit

    result = await AuthService(UserRepository(session)).login(
        phone=payload.phone, password=payload.password
    )
    user = result.user

    await write_audit(
        action="USER_LOGIN",
        actor_user_id=user.id,
        actor_role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        entity_type="user",
        entity_id=str(user.id),
    )

    return TokenResponse(
        access_token=result.access_token,
        role=user.role,
        user_id=str(user.id),
        phone=user.phone,
        full_name=user.full_name,
        guest_id=str(user.guest_id) if user.guest_id else None,
        room_id=str(user.room_id) if user.room_id else None,
        room_number=user.room_number,
        must_change_password=user.must_change_password,
    )


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser) -> MeResponse:
    return MeResponse(
        id=str(user.id),
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=4)
    new_password: str = Field(..., min_length=4)


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    payload: ChangePasswordRequest,
    user: CurrentUser,
    session: SessionDep,
) -> TokenResponse:
    """Change password. Issues new token pair. Clears must_change_password."""
    from src.core.security.hash import hash_password, verify_password
    from src.core.security.jwt import create_access_token

    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="current password is incorrect",
        )
    async with session.begin():
        user.password_hash = hash_password(payload.new_password)
        user.must_change_password = False
        await session.flush()

    token = create_access_token(
        user_id=str(user.id),
        phone=user.phone,
        role=user.role.value,
        guest_id=str(user.guest_id) if user.guest_id else None,
        room_id=str(user.room_id) if user.room_id else None,
        room_number=user.room_number,
    )
    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=str(user.id),
        phone=user.phone,
        full_name=user.full_name,
        guest_id=str(user.guest_id) if user.guest_id else None,
        room_id=str(user.room_id) if user.room_id else None,
        room_number=user.room_number,
        must_change_password=False,
    )
