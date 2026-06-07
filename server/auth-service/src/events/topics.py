"""Channel names auth-service subscribes to and publishes."""

from __future__ import annotations


class Channels:
    # Auth subscribes to these (published by reception-service):
    GUEST_CREDENTIAL_CREATED = "guests.credential_created"
    GUEST_CREDENTIAL_DEACTIVATED = "guests.credential_deactivated"
    GUEST_CREDENTIAL_UPDATED = "guests.credential_updated"

    # Auth publishes these so other services can mirror staff identity
    # locally and never have to call back into auth-service over HTTP.
    USER_CREATED = "users.created"
    USER_UPDATED = "users.updated"
    USER_DEACTIVATED = "users.deactivated"
