"""Authentication use cases. Pure business logic — no FastAPI here."""

from __future__ import annotations

from dataclasses import dataclass

from src.core.security.hash import verify_password
from src.core.security.jwt import create_access_token
from src.domain.enums import UserRole
from src.domain.models import User
from src.infra.repositories.user_repository import UserRepository


class AuthenticationError(Exception):
    """Raised when phone/password do not match or the user is disabled."""


@dataclass(slots=True)
class AuthResult:
    user: User
    access_token: str


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def login(self, *, phone: str, password: str) -> AuthResult:
        user = await self.users.get_by_phone(phone)
        if user is None or not user.is_active:
            raise AuthenticationError("invalid credentials")
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("invalid credentials")
        token = create_access_token(
            user_id=str(user.id),
            phone=user.phone,
            role=user.role.value if isinstance(user.role, UserRole) else str(user.role),
            guest_id=str(user.guest_id) if user.guest_id else None,
            room_id=str(user.room_id) if user.room_id else None,
            room_number=user.room_number,
        )
        return AuthResult(user=user, access_token=token)
