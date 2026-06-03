"""orders.is_billed flag

Revision ID: 0005_orders_is_billed
Revises: 0004_orders
Create Date: 2026-06-03 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_orders_is_billed"
down_revision: Union[str, Sequence[str], None] = "0004_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "reception"


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "is_billed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "orders",
        sa.Column("billed_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("orders", "billed_at", schema=SCHEMA)
    op.drop_column("orders", "is_billed", schema=SCHEMA)
