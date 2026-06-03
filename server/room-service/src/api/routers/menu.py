"""Menu CRUD + availability toggle.

Manager controls the catalogue; reception (the order-taker) gets read-only
access to populate the order form. Cleaner / technician do not see this
router at all — they have no business with the kitchen menu.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError

from src.api.dependencies import SessionDep, require_role
from src.api.schemas.menu import (
    AvailabilityUpdate,
    MenuItemCreate,
    MenuItemOut,
    MenuItemUpdate,
)
from src.domain.enums import UserRole
from src.infra.repositories.menu_repository import MenuRepository

router = APIRouter(prefix="/menu", tags=["menu"])

CAN_VIEW = (UserRole.MANAGER, UserRole.RECEPTION)
CAN_EDIT = (UserRole.MANAGER,)


@router.get("", response_model=list[MenuItemOut])
async def list_menu(
    session: SessionDep,
    available_only: bool = False,
    _=Depends(require_role(*CAN_VIEW)),
) -> list[MenuItemOut]:
    items = await MenuRepository(session).list_all(available_only=available_only)
    return [MenuItemOut.model_validate(i, from_attributes=True) for i in items]


@router.post("", response_model=MenuItemOut, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    payload: MenuItemCreate,
    session: SessionDep,
    _=Depends(require_role(*CAN_EDIT)),
) -> MenuItemOut:
    repo = MenuRepository(session)
    try:
        async with session.begin():
            item = await repo.create(
                name=payload.name,
                category=payload.category,
                price_minor_units=payload.price_minor_units,
                prep_minutes=payload.prep_minutes,
                is_available=payload.is_available,
            )
            snapshot = MenuItemOut.model_validate(item, from_attributes=True)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "duplicate_name", "message": "menu item name must be unique"},
        ) from exc
    return snapshot


@router.put("/{item_id}", response_model=MenuItemOut)
async def update_menu_item(
    item_id: uuid.UUID,
    payload: MenuItemUpdate,
    session: SessionDep,
    _=Depends(require_role(*CAN_EDIT)),
) -> MenuItemOut:
    repo = MenuRepository(session)
    async with session.begin():
        item = await repo.get(item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="menu item not found")
        try:
            await repo.update(
                item,
                name=payload.name,
                category=payload.category,
                price_minor_units=payload.price_minor_units,
                prep_minutes=payload.prep_minutes,
                is_available=payload.is_available,
            )
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "duplicate_name", "message": "menu item name must be unique"},
            ) from exc
        snapshot = MenuItemOut.model_validate(item, from_attributes=True)
    return snapshot


@router.patch("/{item_id}/availability", response_model=MenuItemOut)
async def set_availability(
    item_id: uuid.UUID,
    payload: AvailabilityUpdate,
    session: SessionDep,
    _=Depends(require_role(*CAN_EDIT)),
) -> MenuItemOut:
    """Dedicated toggle so the manager UI can flip availability without
    re-sending the whole record (and without the schema's other fields
    becoming accidentally required)."""
    repo = MenuRepository(session)
    async with session.begin():
        item = await repo.get(item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="menu item not found")
        await repo.update(item, is_available=payload.is_available)
        snapshot = MenuItemOut.model_validate(item, from_attributes=True)
    return snapshot


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_menu_item(
    item_id: uuid.UUID,
    session: SessionDep,
    _=Depends(require_role(*CAN_EDIT)),
) -> Response:
    repo = MenuRepository(session)
    async with session.begin():
        item = await repo.get(item_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="menu item not found")
        await repo.delete(item)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
