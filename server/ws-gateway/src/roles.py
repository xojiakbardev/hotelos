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
    # Guests get order + maintenance + cleaning events, but only for their own
    # room/guest — enforced at the event level by event_targets_guest().
    "guest":     ["orders.*", "maintenance.*", "rooms.cleaning_started", "rooms.cleaned"],
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

# Fields guests must never see (staff IDs, billing breakdowns, internal refs).
GUEST_REDACTED_KEYS: frozenset[str] = frozenset(
    {
        "taken_by_user_id",
        "reported_by_user_id",
        "assigned_technician_id",
        "resolved_by_user_id",
        "cleaner_user_id",
        "total_minor_units",
        "nightly_rate_minor_units",
        "nightly_rate_locked_minor_units",
        "bill_id",
    }
)


def channels_for(role: str) -> list[str]:
    return ROLE_CHANNELS.get(role, [])


def event_targets_guest(payload: dict, guest_id: str | None, room_id: str | None) -> bool:
    """Return True if this event belongs to the given guest's room/guest_id.

    Guests must only receive events about their own orders, maintenance, and
    cleaning. We match on guest_id first, then room_id as a fallback.
    """
    if guest_id and str(payload.get("guest_id", "")) == guest_id:
        return True
    if room_id and str(payload.get("room_id", "")) == room_id:
        return True
    return False


def redact(payload: dict, role: str) -> dict:
    """Return a shallow copy of payload with disallowed keys removed."""
    forbidden: set[str] = set(ALWAYS_REDACTED_KEYS)
    if role != "manager":
        forbidden |= MANAGER_ONLY_KEYS
    if role == "guest":
        forbidden |= GUEST_REDACTED_KEYS
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
