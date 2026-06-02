"""Role-default permission seeding. Real RBAC checks are done by middleware reading role + permission rows."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import UserRole
from src.domain.models import Permission

# Default permission codes granted on user creation, keyed by role.
# Codes are plain strings; downstream services interpret them.
DEFAULT_PERMISSIONS: dict[UserRole, list[str]] = {
    UserRole.MANAGER: [
        "rooms:*",
        "guests:*",
        "reservations:*",
        "orders:*",
        "maintenance:*",
        "housekeeping:*",
        "staff:*",
        "reports:read",
    ],
    UserRole.RECEPTION: [
        "rooms:read",
        "guests:*",
        "reservations:*",
        "orders:*",
        "maintenance:create",
    ],
    UserRole.TECHNICIAN: [
        "maintenance:read",
        "maintenance:resolve",
    ],
    UserRole.CLEANER: [
        "housekeeping:read",
        "housekeeping:update_status",
    ],
}


class PermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_default_entries_for_user(
        self, user_id: uuid.UUID, role: UserRole
    ) -> list[Permission]:
        codes = DEFAULT_PERMISSIONS.get(role, [])
        rows = [Permission(user_id=user_id, code=code, granted=True) for code in codes]
        self.session.add_all(rows)
        await self.session.flush()
        return rows
