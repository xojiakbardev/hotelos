"""rooms and guests

Revision ID: 0002_rooms_and_guests
Revises: 0001_create_schema
Create Date: 2026-06-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_rooms_and_guests"
down_revision: Union[str, Sequence[str], None] = "0001_create_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "reception"


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("room_number", sa.Integer(), nullable=False),
        sa.Column("floor", sa.SmallInteger(), nullable=False),
        sa.Column("room_type", sa.String(length=16), nullable=False),
        sa.Column("proximity", sa.String(length=16), nullable=False),
        sa.Column(
            "cleanliness_status", sa.String(length=16), nullable=False, server_default="clean"
        ),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="available"),
        sa.Column("nightly_rate_minor_units", sa.BigInteger(), nullable=False),
        sa.Column(
            "last_cleaned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_assigned_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("room_number", name="uq_rooms_room_number"),
        schema=SCHEMA,
    )

    op.create_table(
        "guests",
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
        sa.Column(
            "checked_in_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_checkout_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nightly_rate_locked_minor_units", sa.BigInteger(), nullable=False),
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


def downgrade() -> None:
    op.drop_table("guests", schema=SCHEMA)
    op.drop_table("rooms", schema=SCHEMA)
