"""Kitchen-side read-only endpoints.

Room-service does not accept order *writes* — reception owns the lifecycle.
What we expose here is the projected view a manager (or a future kitchen
display) can read.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import SessionDep, require_role
from src.api.schemas.order import OrderMirrorOut
from src.domain.enums import UserRole
from src.infra.repositories.order_mirror_repository import OrderMirrorRepository

router = APIRouter(prefix="/orders", tags=["orders"])

CAN_VIEW = (UserRole.MANAGER, UserRole.RECEPTION)


@router.get("", response_model=list[OrderMirrorOut])
async def list_open_orders(
    session: SessionDep,
    _=Depends(require_role(*CAN_VIEW)),
) -> list[OrderMirrorOut]:
    rows = await OrderMirrorRepository(session).list_open()
    return [OrderMirrorOut.model_validate(o, from_attributes=True) for o in rows]


@router.get("/history", response_model=list[OrderMirrorOut])
async def list_history(
    session: SessionDep,
    _=Depends(require_role(UserRole.MANAGER)),
) -> list[OrderMirrorOut]:
    rows = await OrderMirrorRepository(session).list_all()
    return [OrderMirrorOut.model_validate(o, from_attributes=True) for o in rows]
