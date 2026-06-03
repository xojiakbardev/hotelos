"""Per-role channel subscriptions + payload redaction policy.

This is the single place that decides what each role sees over the WS. Domain
services do not have to know about role policy — they simply publish to topic
channels and ws-gateway filters.
"""

from __future__ import annotations

from typing import Iterable

# Channel patterns each role is allowed to receive.
ROLE_CHANNELS: dict[str, list[str]] = {
    "manager":   ["rooms.*", "guests.*", "orders.*", "bills.*", "maintenance.*", "housekeeping.*", "reservations.*"],
    "reception": ["rooms.*", "guests.*", "orders.*", "maintenance.*", "reservations.*"],
    "technician": ["maintenance.*", "rooms.status"],
    "cleaner":    ["rooms.*", "housekeeping.*"],
}

# Fields that must never reach the browser via WS regardless of role.
ALWAYS_REDACTED_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "password_hash",
        "passport_number",
        "card_number",
        "card_cvv",
        "card_pan",
    }
)

# Fields restricted to manager only.
MANAGER_ONLY_KEYS: frozenset[str] = frozenset({"bill_lines", "payment_method", "ssn"})


def channels_for(role: str) -> list[str]:
    return ROLE_CHANNELS.get(role, [])


def redact(payload: dict, role: str) -> dict:
    """Return a shallow copy of payload with disallowed keys removed."""
    forbidden: set[str] = set(ALWAYS_REDACTED_KEYS)
    if role != "manager":
        forbidden |= MANAGER_ONLY_KEYS
    return {k: v for k, v in payload.items() if k not in forbidden}


def channel_matches(channel: str, patterns: Iterable[str]) -> bool:
    """Glob-ish prefix match. Patterns may end in `.*` or be exact."""
    for p in patterns:
        if p.endswith(".*"):
            if channel.startswith(p[:-2] + "."):
                return True
        elif p == channel:
            return True
    return False
