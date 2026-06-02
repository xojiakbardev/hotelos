"""Public auth endpoints: POST /login, GET /me."""

from __future__ import annotations

from fastapi import APIRouter

from src.api.dependencies import CurrentUser, SessionDep
from src.api.schemas.auth import LoginRequest, MeResponse, TokenResponse
from src.infra.repositories.user_repository import UserRepository
from src.services.auth_service import AuthService

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    result = await AuthService(UserRepository(session)).login(
        phone=payload.phone, password=payload.password
    )
    user = result.user
    return TokenResponse(
        access_token=result.access_token,
        role=user.role,
        user_id=str(user.id),
        phone=user.phone,
        full_name=user.full_name,
    )


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser) -> MeResponse:
    return MeResponse(
        id=str(user.id),
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )
