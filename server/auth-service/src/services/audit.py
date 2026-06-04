"""Audit log writer. Called from auth endpoints and event handlers."""

from __future__ import annotations

import uuid
from typing import Any

from src.core.db import async_session_factory
from src.domain.models import AuditLog


async def write_audit(
    *,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    actor_role: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write an audit log entry."""
    async with async_session_factory() as session:
        async with session.begin():
            log = AuditLog(
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata_json=metadata or {},
            )
            session.add(log)
