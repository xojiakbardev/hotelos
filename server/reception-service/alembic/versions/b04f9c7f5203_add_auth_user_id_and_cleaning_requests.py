"""add auth_user_id and cleaning_requests

Revision ID: b04f9c7f5203
Revises: 0007_reservations
Create Date: 2026-06-03 14:12:28.712455
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b04f9c7f5203"
down_revision: Union[str, Sequence[str], None] = "0007_reservations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "reception"


def upgrade() -> None:
    op.add_column(
        "guests",
        sa.Column("auth_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_table(
        "cleaning_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "guest_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.guests.id"),
            nullable=False,
        ),
        sa.Column(
            "room_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.rooms.id"),
            nullable=False,
        ),
        sa.Column("room_number", sa.Integer(), nullable=False),
        sa.Column("floor", sa.SmallInteger(), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column(
            "preferred_time", sa.String(length=16), nullable=False, server_default="afternoon"
        ),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        op.f("ix_reception_cleaning_requests_guest_id"),
        "cleaning_requests",
        ["guest_id"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_reception_cleaning_requests_guest_id"),
        table_name="cleaning_requests",
        schema=SCHEMA,
    )
    op.drop_table("cleaning_requests", schema=SCHEMA)
    op.drop_column("guests", "auth_user_id", schema=SCHEMA)
