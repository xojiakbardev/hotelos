"""add freshness_score and dynamic_price

Revision ID: 8e3e8bdec074
Revises: b04f9c7f5203
Create Date: 2026-06-03 17:01:04.580576
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8e3e8bdec074'
down_revision: Union[str, Sequence[str], None] = 'b04f9c7f5203'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The cleaning_requests index drop/recreate that Alembic auto-generated
    # here was a false positive — the prior migration (b04f9c7f5203) now
    # creates the table with the canonical `ix_reception_cleaning_requests_guest_id`
    # name, so there is nothing to rename. Only the two new room columns
    # remain to be added.
    op.add_column(
        "rooms",
        sa.Column("freshness_score", sa.Float(), server_default="1.0", nullable=False),
        schema="reception",
    )
    op.add_column(
        "rooms",
        sa.Column(
            "dynamic_price_minor_units",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
        schema="reception",
    )


def downgrade() -> None:
    op.drop_column("rooms", "dynamic_price_minor_units", schema="reception")
    op.drop_column("rooms", "freshness_score", schema="reception")
