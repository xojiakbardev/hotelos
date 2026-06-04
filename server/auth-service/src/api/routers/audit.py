"""Audit log endpoints — manager-only read access."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from src.api.dependencies import SessionDep, require_role
from src.domain.enums import UserRole
from src.domain.models import AuditLog, User

router = APIRouter(prefix="/audit-logs", tags=["audit"])


class AuditLogOut(BaseModel):
    id: str
    actor_user_id: str | None
    actor_role: str | None
    actor_phone: str | None
    actor_name: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    metadata_json: dict
    created_at: datetime


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    total: int
    offset: int
    limit: int


@router.get("", response_model=AuditLogPage)
async def list_audit_logs(
    session: SessionDep,
    _=Depends(require_role(UserRole.MANAGER)),
    action: str | None = None,
    entity_type: str | None = None,
    actor_role: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
) -> AuditLogPage:
    """Paginated audit log with optional filters."""
    stmt = select(AuditLog)
    count_stmt = select(func.count(AuditLog.id))

    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
        count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)
    if actor_role:
        stmt = stmt.where(AuditLog.actor_role == actor_role)
        count_stmt = count_stmt.where(AuditLog.actor_role == actor_role)

    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()

    # Batch-load actor users for phone/name display
    actor_ids = {r.actor_user_id for r in rows if r.actor_user_id}
    users_map: dict[uuid.UUID, User] = {}
    if actor_ids:
        user_stmt = select(User).where(User.id.in_(actor_ids))
        users = (await session.execute(user_stmt)).scalars().all()
        users_map = {u.id: u for u in users}

    return AuditLogPage(
        items=[
            AuditLogOut(
                id=str(r.id),
                actor_user_id=str(r.actor_user_id) if r.actor_user_id else None,
                actor_role=r.actor_role,
                actor_phone=users_map[r.actor_user_id].phone if r.actor_user_id and r.actor_user_id in users_map else None,
                actor_name=users_map[r.actor_user_id].full_name if r.actor_user_id and r.actor_user_id in users_map else None,
                action=r.action,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                metadata_json=r.metadata_json,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=total,
        offset=offset,
        limit=limit,
    )
