"""Order lifecycle rules.

Single source of truth for the room-service order state machine:

    received → preparing → delivering → delivered (terminal)

No skipping, no going back. Cancellation is out of scope for v1 — if a
guest wants to cancel a delivered coffee we'd need a separate refund flow,
not a state regression.
"""

from __future__ import annotations

from src.domain.enums import ORDER_LIFECYCLE, OrderStatus


class IllegalTransition(Exception):
    """Raised when advance() is called on an order in a terminal state."""

    def __init__(self, from_status: OrderStatus) -> None:
        super().__init__(f"cannot advance from terminal state '{from_status.value}'")
        self.from_status = from_status


def next_status(current: OrderStatus) -> OrderStatus:
    nxt = ORDER_LIFECYCLE.get(current)
    if nxt is None:
        raise IllegalTransition(current)
    return nxt


def is_terminal(status: OrderStatus) -> bool:
    return ORDER_LIFECYCLE.get(status) is None
