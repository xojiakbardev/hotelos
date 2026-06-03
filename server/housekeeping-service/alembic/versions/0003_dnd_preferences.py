"""cleaning_queue_entries.dnd + cleaning_preference

Revision ID: 0003_dnd_preferences
Revises: 0002_cleaning_queue
Create Date: 2026-06-03 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_dnd_preferences"
down_revision: Union[str, Sequence[str], None] = "0002_cleaning_queue"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "housekeeping"


def upgrade() -> None:
    op.add_column(
        "cleaning_queue_entries",
        sa.Column(
            "do_not_disturb",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "cleaning_queue_entries",
        sa.Column(
            "cleaning_preference",
            sa.String(length=16),
            nullable=False,
            server_default="afternoon",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "cleaning_queue_entries",
        sa.Column("cleaning_preference_note", sa.String(length=200), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("cleaning_queue_entries", "cleaning_preference_note", schema=SCHEMA)
    op.drop_column("cleaning_queue_entries", "cleaning_preference", schema=SCHEMA)
    op.drop_column("cleaning_queue_entries", "do_not_disturb", schema=SCHEMA)
