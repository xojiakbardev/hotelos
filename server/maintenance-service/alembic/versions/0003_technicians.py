"""technicians projection + denormalised tech snapshot on issues

Revision ID: 0003_technicians
Revises: 0002_issues
Create Date: 2026-06-07 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_technicians"
down_revision: Union[str, Sequence[str], None] = "0002_issues"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "maintenance"


def upgrade() -> None:
    op.create_table(
        "technicians",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "issues",
        sa.Column("assigned_technician_name", sa.String(length=120), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "issues",
        sa.Column("assigned_technician_phone", sa.String(length=32), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("issues", "assigned_technician_phone", schema=SCHEMA)
    op.drop_column("issues", "assigned_technician_name", schema=SCHEMA)
    op.drop_table("technicians", schema=SCHEMA)
