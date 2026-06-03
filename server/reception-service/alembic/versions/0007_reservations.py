"""reservations table

Revision ID: 0007_reservations
Revises: 0006_guest_dnd_preferences
Create Date: 2026-06-03 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_reservations"
down_revision: Union[str, Sequence[str], None] = "0006_guest_dnd_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "reception"


def upgrade() -> None:
    op.create_table(
        "reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("passport_number", sa.String(length=40), nullable=True),
        sa.Column(
            "room_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.rooms.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("check_in_date", sa.Date(), nullable=False),
        sa.Column("check_out_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("nightly_rate_locked_minor_units", sa.BigInteger(), nullable=False),
        sa.Column(
            "guest_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.guests.id"),
            nullable=True,
        ),
        sa.Column(
            "status_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
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
        schema=SCHEMA,
    )
    op.create_index(
        "ix_reservations_room_dates",
        "reservations",
        ["room_id", "check_in_date", "check_out_date"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_reservations_room_dates", table_name="reservations", schema=SCHEMA)
    op.drop_table("reservations", schema=SCHEMA)
