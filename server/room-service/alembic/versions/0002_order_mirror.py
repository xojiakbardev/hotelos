"""orders mirror

Revision ID: 0002_order_mirror
Revises: 0001_create_schema
Create Date: 2026-06-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_order_mirror"
down_revision: Union[str, Sequence[str], None] = "0001_create_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "room_service"


def upgrade() -> None:
    op.create_table(
        "orders_mirror",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("guest_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("room_number", sa.Integer(), nullable=False),
        sa.Column("floor", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "items",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("total_minor_units", sa.BigInteger(), nullable=False),
        sa.Column("taken_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("preparing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivering_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
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
    op.drop_table("orders_mirror", schema=SCHEMA)
