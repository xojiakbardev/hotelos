"""Room assignment algorithm.

When a guest checks in, this function picks the best available room according
to the rules defined in `docs/decisions.md` (D-RoomAssignment). The matching
flowchart lives in `docs/algorithms/room_assignment.flowchart.svg`.

Rules — in order of importance:

  1. Room TYPE must match the guest's booking
     (single / double / suite / accessible).
  2. Cleanliness must be 'clean'. Dirty, in-cleaning, and maintenance rooms
     are excluded by the underlying query.
  3. Among matching candidates, the room that has been clean the *longest*
     wins. This rotates inventory fairly across the floor instead of always
     picking the most recently cleaned suite.
  4. If the guest expressed a floor preference and at least one matching
     room sits on that floor, restrict to those rooms. Otherwise fall back
     to all matches — we never refuse a guest just because their favourite
     floor is full.
  5. If the guest expressed an elevator / stairs proximity preference, use
     it as the final tiebreaker.

The shortlist returned by `RoomRepository.find_assignable` already has the
FOR UPDATE SKIP LOCKED clause that prevents two simultaneous check-ins from
double-booking a single room (test scenario TS-06).

This module is pure logic + one repository call. HTTP, transactions, and
event publishing all live in `api/routers/guests.py::check_in`.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.enums import Proximity, RoomType
from src.domain.models import Room
from src.infra.repositories.room_repository import RoomRepository


class NoRoomsAvailable(Exception):
    """Raised when no clean room of the requested type is available right now."""

    def __init__(self, room_type: RoomType) -> None:
        super().__init__(f"no rooms available for type {room_type.value}")
        self.room_type = room_type


@dataclass(slots=True, frozen=True)
class AssignmentRequest:
    room_type: RoomType
    floor_preference: int | None = None
    proximity_preference: Proximity | None = None


async def pick_room(req: AssignmentRequest, rooms: RoomRepository) -> Room:
    """Return the single best room for `req`. The caller owns the transaction.

    Raises `NoRoomsAvailable` when nothing matches the type filter.
    """
    # Step 1 + 2 + 3: SQL handles type, cleanliness, status, and the
    # longest-clean ordering. Each returned row is also locked so a
    # concurrent check-in can't take it.
    candidates = await rooms.find_assignable(room_type=req.room_type)

    if not candidates:
        raise NoRoomsAvailable(req.room_type)

    # Step 4: floor preference is a SOFT filter. Honour it when possible,
    # but never refuse the guest just because their favourite floor is full.
    if req.floor_preference is not None:
        on_preferred_floor = [r for r in candidates if r.floor == req.floor_preference]
        if on_preferred_floor:
            candidates = on_preferred_floor

    # Step 5: proximity is the final tiebreaker. Stable sort so the existing
    # longest-clean ordering is preserved when proximity scores tie.
    if req.proximity_preference is not None:
        candidates.sort(
            key=lambda r: 0 if r.proximity == req.proximity_preference.value else 1
        )

    return candidates[0]
