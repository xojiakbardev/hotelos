"""Data access for maintenance issues."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import IssueStatus
from src.domain.models import Issue


class IssueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, issue_id: uuid.UUID) -> Issue | None:
        return await self.session.get(Issue, issue_id)

    async def list_open(self) -> list[Issue]:
        """All issues not yet resolved, in DB-insertion order. Priority
        ordering is applied by `priority_queue.rank_by_priority`."""
        stmt = select(Issue).where(Issue.status != IssueStatus.RESOLVED.value)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_unassigned(self) -> list[Issue]:
        stmt = select(Issue).where(Issue.status == IssueStatus.REPORTED.value)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_technician(self, technician_id: uuid.UUID) -> list[Issue]:
        stmt = (
            select(Issue)
            .where(
                Issue.assigned_technician_id == technician_id,
                Issue.status != IssueStatus.RESOLVED.value,
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_history(self, limit: int = 50) -> list[Issue]:
        stmt = (
            select(Issue)
            .where(Issue.status == IssueStatus.RESOLVED.value)
            .order_by(Issue.resolved_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(
        self,
        *,
        room_id: uuid.UUID,
        room_number: int,
        floor: int,
        urgency: str,
        description: str,
        reported_by_user_id: uuid.UUID,
    ) -> Issue:
        issue = Issue(
            room_id=room_id,
            room_number=room_number,
            floor=floor,
            urgency=urgency,
            description=description,
            reported_by_user_id=reported_by_user_id,
            status=IssueStatus.REPORTED.value,
        )
        self.session.add(issue)
        await self.session.flush()
        return issue

    async def mark_assigned(
        self,
        issue: Issue,
        *,
        technician_id: uuid.UUID,
        technician_name: str | None = None,
        technician_phone: str | None = None,
    ) -> None:
        issue.status = IssueStatus.ASSIGNED.value
        issue.assigned_technician_id = technician_id
        issue.assigned_technician_name = technician_name
        issue.assigned_technician_phone = technician_phone
        issue.assigned_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def mark_resolved(self, issue: Issue, *, resolved_by_user_id: uuid.UUID) -> None:
        issue.status = IssueStatus.RESOLVED.value
        issue.resolved_by_user_id = resolved_by_user_id
        issue.resolved_at = datetime.now(timezone.utc)
        await self.session.flush()
