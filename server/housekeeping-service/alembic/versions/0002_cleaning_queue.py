"""cleaning queue

Revision ID: 0002_cleaning_queue
Revises: 0001_create_schema
Create Date: 2026-06-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_cleaning_queue"
down_revision: Union[str, Sequence[str], None] = "0001_create_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "housekeeping"


def upgrade() -> None:
    op.create_table(
        "cleaning_queue_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("room_number", sa.Integer(), nullable=False),
        sa.Column("floor", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_cleaner_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.UniqueConstraint("room_id", "status", name="uq_cleaning_queue_room_active"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("cleaning_queue_entries", schema=SCHEMA)
