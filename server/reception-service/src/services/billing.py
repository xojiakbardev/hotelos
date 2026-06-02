"""Billing algorithm.

Pure function — produces a `BillSnapshot` from inputs and never touches the
DB or the broker. The check-out endpoint is responsible for persisting and
publishing.

Formula (brief 1.2):

    total = nightly_rate × nights
          + Σ room_service_charges
          + Σ extras
          − Σ discounts                  (clamped to 0)

Edge cases the algorithm handles:

  * **Early check-out** — `nights` is clamped to a minimum of 1, so a guest
    who leaves the same afternoon is still billed for one night.
  * **Zero charges** — `room_service_charges` / `extras` / `discounts` are
    optional iterables; empty is fine.
  * **Discount overshoot** — if discounts exceed everything else, the bill
    floors at zero. We do not refund the guest negative money.

Money is everywhere in minor units (e.g. tiyin) to avoid float drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class BillSnapshot:
    nights: int
    nightly_rate_minor_units: int
    room_cost_minor_units: int
    room_service_charges_minor_units: int
    extras_minor_units: int
    discount_minor_units: int
    total_minor_units: int


def compute_bill(
    *,
    nightly_rate_minor_units: int,
    nights: int,
    room_service_charges: Iterable[int] = (),
    extras: Iterable[int] = (),
    discounts: Iterable[int] = (),
) -> BillSnapshot:
    nights = max(1, nights)
    room_cost = nightly_rate_minor_units * nights
    rs_total = sum(room_service_charges)
    extras_total = sum(extras)
    discount_total = sum(discounts)
    total = max(0, room_cost + rs_total + extras_total - discount_total)
    return BillSnapshot(
        nights=nights,
        nightly_rate_minor_units=nightly_rate_minor_units,
        room_cost_minor_units=room_cost,
        room_service_charges_minor_units=rs_total,
        extras_minor_units=extras_total,
        discount_minor_units=discount_total,
        total_minor_units=total,
    )
