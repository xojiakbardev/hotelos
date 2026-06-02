"""Maintenance endpoints.

  POST /issues                         report a new problem (manager + reception)
  GET  /queue                          priority-ordered open queue (manager + technician)
  GET  /my                             technician's claimed-but-unresolved issues
  POST /issues/{id}/assign-me          technician claims an issue
  POST /issues/{id}/resolve            technician (or assignee/manager) marks done
  GET  /history                        last 50 resolved issues (manager)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import (
    CurrentUserDep,
    PublisherDep,
    SessionDep,
    require_role,
)
from src.api.schemas.issue import IssueOut, IssueReport
from src.domain.enums import IssueStatus, UserRole
from src.events.topics import Channels
from src.infra.repositories.issue_repository import IssueRepository
from src.services.priority_queue import rank_by_priority

router = APIRouter(tags=["maintenance"])

CAN_REPORT = (UserRole.MANAGER, UserRole.RECEPTION)
CAN_WORK = (UserRole.MANAGER, UserRole.TECHNICIAN)
CAN_VIEW = (UserRole.MANAGER, UserRole.TECHNICIAN, UserRole.RECEPTION)


@router.post("/issues", response_model=IssueOut, status_code=status.HTTP_201_CREATED)
async def report_issue(
    payload: IssueReport,
    session: SessionDep,
    publisher: PublisherDep,
    user: CurrentUserDep,
    _=Depends(require_role(*CAN_REPORT)),
) -> IssueOut:
    repo = IssueRepository(session)
    async with session.begin():
        issue = await repo.create(
            room_id=payload.room_id,
            room_number=payload.room_number,
            floor=payload.floor,
            urgency=payload.urgency.value,
            description=payload.description,
            reported_by_user_id=uuid.UUID(user.id),
        )
        snapshot = IssueOut.model_validate(issue, from_attributes=True)

    await publisher.publish(
        channel=Channels.MAINTENANCE_REPORTED,
        payload={
            "issue_id": str(snapshot.id),
            "room_id": str(snapshot.room_id),
            "room_number": snapshot.room_number,
            "floor": snapshot.floor,
            "urgency": snapshot.urgency.value,
            "description": snapshot.description,
            "reported_by_user_id": user.id,
            "reported_at": snapshot.reported_at.isoformat(),
        },
    )
    return snapshot


@router.get("/queue", response_model=list[IssueOut])
async def get_queue(
    session: SessionDep,
    _=Depends(require_role(*CAN_VIEW)),
) -> list[IssueOut]:
    """Return open issues in priority order — what the dashboard shows
    as "next up". Uses `heapq` under the hood."""
    open_issues = await IssueRepository(session).list_open()
    ranked = rank_by_priority(open_issues)
    return [IssueOut.model_validate(i, from_attributes=True) for i in ranked]


@router.get("/my", response_model=list[IssueOut])
async def get_my_queue(
    session: SessionDep,
    user: CurrentUserDep,
    _=Depends(require_role(UserRole.TECHNICIAN, UserRole.MANAGER)),
) -> list[IssueOut]:
    issues = await IssueRepository(session).list_for_technician(uuid.UUID(user.id))
    return [IssueOut.model_validate(i, from_attributes=True) for i in rank_by_priority(issues)]


@router.post("/issues/{issue_id}/assign-me", response_model=IssueOut)
async def assign_to_me(
    issue_id: uuid.UUID,
    session: SessionDep,
    publisher: PublisherDep,
    user: CurrentUserDep,
    _=Depends(require_role(UserRole.TECHNICIAN, UserRole.MANAGER)),
) -> IssueOut:
    repo = IssueRepository(session)
    async with session.begin():
        issue = await repo.get(issue_id)
        if issue is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="issue not found")
        if issue.status != IssueStatus.REPORTED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "wrong_state",
                    "message": f"cannot claim issue in status '{issue.status}'",
                    "current_status": issue.status,
                },
            )
        await repo.mark_assigned(issue, technician_id=uuid.UUID(user.id))
        snapshot = IssueOut.model_validate(issue, from_attributes=True)

    await publisher.publish(
        channel=Channels.MAINTENANCE_ASSIGNED,
        payload={
            "issue_id": str(snapshot.id),
            "room_id": str(snapshot.room_id),
            "room_number": snapshot.room_number,
            "technician_user_id": user.id,
            "assigned_at": snapshot.assigned_at.isoformat() if snapshot.assigned_at else None,
        },
    )
    return snapshot


@router.post("/issues/{issue_id}/resolve", response_model=IssueOut)
async def resolve_issue(
    issue_id: uuid.UUID,
    session: SessionDep,
    publisher: PublisherDep,
    user: CurrentUserDep,
    _=Depends(require_role(UserRole.TECHNICIAN, UserRole.MANAGER)),
) -> IssueOut:
    repo = IssueRepository(session)
    async with session.begin():
        issue = await repo.get(issue_id)
        if issue is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="issue not found")
        if issue.status == IssueStatus.RESOLVED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "already_resolved",
                    "message": "issue already resolved",
                },
            )
        await repo.mark_resolved(issue, resolved_by_user_id=uuid.UUID(user.id))
        snapshot = IssueOut.model_validate(issue, from_attributes=True)

    await publisher.publish(
        channel=Channels.MAINTENANCE_RESOLVED,
        payload={
            "issue_id": str(snapshot.id),
            "room_id": str(snapshot.room_id),
            "room_number": snapshot.room_number,
            "floor": snapshot.floor,
            "resolved_by_user_id": user.id,
            "resolved_at": snapshot.resolved_at.isoformat() if snapshot.resolved_at else None,
        },
    )
    return snapshot


@router.get("/history", response_model=list[IssueOut])
async def history(
    session: SessionDep,
    _=Depends(require_role(UserRole.MANAGER)),
) -> list[IssueOut]:
    rows = await IssueRepository(session).list_history()
    return [IssueOut.model_validate(i, from_attributes=True) for i in rows]
