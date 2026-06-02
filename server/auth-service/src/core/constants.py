"""Named constants. Promoted from anywhere a magic number would otherwise appear."""

from __future__ import annotations

# Bcrypt cost factor — 12 is a good balance for 2026 hardware.
BCRYPT_COST: int = 12

# JWT subject + claim names used across services.
JWT_CLAIM_SUB: str = "sub"
JWT_CLAIM_PHONE: str = "phone"
JWT_CLAIM_ROLE: str = "role"

# Phone validation: E.164-ish, 10-15 digits, optional leading +.
PHONE_REGEX: str = r"^\+?[1-9]\d{9,14}$"

# Header used by nginx to propagate a per-request trace id.
TRACE_ID_HEADER: str = "X-Request-Id"
