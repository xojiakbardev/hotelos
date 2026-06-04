"""Guest credential generation at check-in.

Produces a short numeric PIN that reception hands to the guest on paper.
The PIN is hashed with bcrypt before being published to the broker so
auth-service never sees the plain text.
"""

from __future__ import annotations

import secrets

import bcrypt

PIN_LENGTH: int = 4
BCRYPT_COST: int = 12


def generate_guest_pin(length: int = PIN_LENGTH) -> str:
    """Generate a cryptographically random numeric PIN."""
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def hash_pin(pin: str) -> str:
    """Hash a PIN using bcrypt (same scheme as auth-service passwords)."""
    salt = bcrypt.gensalt(rounds=BCRYPT_COST)
    return bcrypt.hashpw(pin.encode("utf-8"), salt).decode("utf-8")
