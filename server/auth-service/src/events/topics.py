"""Channel names auth-service subscribes to."""

from __future__ import annotations


class Channels:
    # Auth subscribes to these (published by reception-service):
    GUEST_CREDENTIAL_CREATED = "guests.credential_created"
    GUEST_CREDENTIAL_DEACTIVATED = "guests.credential_deactivated"
    GUEST_CREDENTIAL_UPDATED = "guests.credential_updated"
