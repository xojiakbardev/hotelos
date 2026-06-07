"""maintenance_projection table

Revision ID: 0008_maintenance_projection
Revises: 8e3e8bdec074
Create Date: 2026-06-07 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_maintenance_projection"
down_revision: Union[str, Sequence[str], None] = "8e3e8bdec074"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "reception"


def upgrade() -> None:
    op.create_table(
        "maintenance_projection",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("guest_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("room_number", sa.Integer(), nullable=False),
        sa.Column("floor", sa.SmallInteger(), nullable=False),
        sa.Column("urgency", sa.String(length=16), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="reported"),
        sa.Column("technician_name", sa.String(length=120), nullable=True),
        sa.Column("technician_phone", sa.String(length=32), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("maintenance_projection", schema=SCHEMA)
