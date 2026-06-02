"""Room-service channel names."""

from __future__ import annotations


class Channels:
    # Room-service subscribes to these (reception publishes them):
    ORDER_RECEIVED = "orders.received"
    ORDER_PREPARING = "orders.preparing"
    ORDER_DELIVERING = "orders.delivering"
    ORDER_DELIVERED = "orders.delivered"
