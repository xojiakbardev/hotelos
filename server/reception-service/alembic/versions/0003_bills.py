"""bills

Revision ID: 0003_bills
Revises: 0002_rooms_and_guests
Create Date: 2026-06-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_bills"
down_revision: Union[str, Sequence[str], None] = "0002_rooms_and_guests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "reception"


def upgrade() -> None:
    op.create_table(
        "bills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "guest_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.guests.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "room_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.rooms.id"),
            nullable=False,
        ),
        sa.Column("nights", sa.Integer(), nullable=False),
        sa.Column("nightly_rate_minor_units", sa.BigInteger(), nullable=False),
        sa.Column("room_cost_minor_units", sa.BigInteger(), nullable=False),
        sa.Column(
            "room_service_charges_minor_units",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("extras_minor_units", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("discount_minor_units", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_minor_units", sa.BigInteger(), nullable=False),
        sa.Column(
            "finalized_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("bills", schema=SCHEMA)
