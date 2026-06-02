"""JWT decode for maintenance-service.

Reception only verifies tokens that auth-service has signed. Signing logic
lives in auth-service. This module is intentionally tiny so the dependency
surface stays small — one library (python-jose) and the shared secret.
"""

from __future__ import annotations

from typing import Any

from jose import JWTError, jwt

from src.core.config import settings


class InvalidTokenError(Exception):
    """Raised when a presented JWT cannot be decoded or has expired."""


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
