"""create maintenance schema

Revision ID: 0001_create_schema
Revises:
Create Date: 2026-06-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0001_create_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "maintenance"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')


def downgrade() -> None:
    pass
