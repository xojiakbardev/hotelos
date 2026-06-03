"""guests.do_not_disturb + cleaning_preference

Revision ID: 0006_guest_dnd_preferences
Revises: 0005_orders_is_billed
Create Date: 2026-06-03 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_guest_dnd_preferences"
down_revision: Union[str, Sequence[str], None] = "0005_orders_is_billed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "reception"


def upgrade() -> None:
    op.add_column(
        "guests",
        sa.Column(
            "do_not_disturb",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "guests",
        sa.Column(
            "cleaning_preference",
            sa.String(length=16),
            nullable=False,
            server_default="afternoon",
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "guests",
        sa.Column("cleaning_preference_note", sa.String(length=200), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("guests", "cleaning_preference_note", schema=SCHEMA)
    op.drop_column("guests", "cleaning_preference", schema=SCHEMA)
    op.drop_column("guests", "do_not_disturb", schema=SCHEMA)
