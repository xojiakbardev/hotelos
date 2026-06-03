"""menu_items

Revision ID: 0003_menu_items
Revises: 0002_order_mirror
Create Date: 2026-06-03 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_menu_items"
down_revision: Union[str, Sequence[str], None] = "0002_order_mirror"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "room_service"


def upgrade() -> None:
    op.create_table(
        "menu_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("price_minor_units", sa.BigInteger(), nullable=False),
        sa.Column("prep_minutes", sa.SmallInteger(), nullable=False, server_default="10"),
        sa.Column(
            "is_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_menu_items_name"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("menu_items", schema=SCHEMA)
