#!/usr/bin/env python
"""Management CLI for reception-service.

Commands:
  makemigrations <message>   — alembic revision --autogenerate -m "<message>"
  migrate                    — alembic upgrade head
  seedrooms                  — idempotently seed the 2-floor × 10-room demo inventory
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import click
from sqlalchemy import select

from src.core.db import async_session_factory
from src.domain.enums import Proximity, RoomType
from src.domain.models import Room


@click.group()
def cli() -> None:
    """reception-service management commands."""


@cli.command()
@click.argument("message")
def makemigrations(message: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", message],
        capture_output=True,
        text=True,
    )
    click.echo(result.stdout)
    if result.returncode != 0:
        click.echo(result.stderr, err=True)
        raise click.Abort()


@cli.command()
def migrate() -> None:
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"])
    if result.returncode != 0:
        raise click.Abort()


# Demo inventory: 2 floors × 10 rooms = 20 rooms total.
# Mix of types and proximities so the assignment algorithm has interesting
# choices to make during a demo. The order matters — `last_cleaned_at` is
# staggered by index so the "longest clean wins" tiebreaker produces
# deterministic picks for TS-01 testing.
_DEMO_ROOMS: list[dict] = [
    {"number": 101, "floor": 1, "type": RoomType.SINGLE,     "proximity": Proximity.ELEVATOR, "rate_minor": 5000},
    {"number": 102, "floor": 1, "type": RoomType.SINGLE,     "proximity": Proximity.STAIRS,   "rate_minor": 5000},
    {"number": 103, "floor": 1, "type": RoomType.DOUBLE,     "proximity": Proximity.ELEVATOR, "rate_minor": 8000},
    {"number": 104, "floor": 1, "type": RoomType.DOUBLE,     "proximity": Proximity.ELEVATOR, "rate_minor": 8000},
    {"number": 105, "floor": 1, "type": RoomType.DOUBLE,     "proximity": Proximity.STAIRS,   "rate_minor": 8000},
    {"number": 106, "floor": 1, "type": RoomType.DOUBLE,     "proximity": Proximity.STAIRS,   "rate_minor": 8000},
    {"number": 107, "floor": 1, "type": RoomType.SUITE,      "proximity": Proximity.ELEVATOR, "rate_minor": 20000},
    {"number": 108, "floor": 1, "type": RoomType.SUITE,      "proximity": Proximity.STAIRS,   "rate_minor": 20000},
    {"number": 109, "floor": 1, "type": RoomType.ACCESSIBLE, "proximity": Proximity.ELEVATOR, "rate_minor": 10000},
    {"number": 110, "floor": 1, "type": RoomType.ACCESSIBLE, "proximity": Proximity.ELEVATOR, "rate_minor": 10000},
    {"number": 201, "floor": 2, "type": RoomType.SINGLE,     "proximity": Proximity.ELEVATOR, "rate_minor": 5500},
    {"number": 202, "floor": 2, "type": RoomType.SINGLE,     "proximity": Proximity.STAIRS,   "rate_minor": 5500},
    {"number": 203, "floor": 2, "type": RoomType.DOUBLE,     "proximity": Proximity.ELEVATOR, "rate_minor": 8500},
    {"number": 204, "floor": 2, "type": RoomType.DOUBLE,     "proximity": Proximity.ELEVATOR, "rate_minor": 8500},
    {"number": 205, "floor": 2, "type": RoomType.DOUBLE,     "proximity": Proximity.STAIRS,   "rate_minor": 8500},
    {"number": 206, "floor": 2, "type": RoomType.DOUBLE,     "proximity": Proximity.STAIRS,   "rate_minor": 8500},
    {"number": 207, "floor": 2, "type": RoomType.SUITE,      "proximity": Proximity.ELEVATOR, "rate_minor": 22000},
    {"number": 208, "floor": 2, "type": RoomType.SUITE,      "proximity": Proximity.STAIRS,   "rate_minor": 22000},
    {"number": 209, "floor": 2, "type": RoomType.ACCESSIBLE, "proximity": Proximity.ELEVATOR, "rate_minor": 10500},
    {"number": 210, "floor": 2, "type": RoomType.ACCESSIBLE, "proximity": Proximity.ELEVATOR, "rate_minor": 10500},
]


@cli.command()
def seedrooms() -> None:
    """Insert the demo inventory. Skips rooms that already exist."""

    async def _run() -> None:
        now = datetime.now(timezone.utc)
        async with async_session_factory() as session:
            async with session.begin():
                existing_numbers = set(
                    (await session.execute(select(Room.room_number))).scalars().all()
                )
                created = 0
                for idx, r in enumerate(_DEMO_ROOMS):
                    if r["number"] in existing_numbers:
                        continue
                    # Stagger `last_cleaned_at` backwards by minutes so the
                    # assignment algorithm has deterministic ordering: room
                    # 101 is "oldest clean" → wins first when type matches.
                    last_cleaned = now - timedelta(minutes=(len(_DEMO_ROOMS) - idx))
                    session.add(
                        Room(
                            room_number=r["number"],
                            floor=r["floor"],
                            room_type=r["type"].value,
                            proximity=r["proximity"].value,
                            cleanliness_status="clean",
                            status="available",
                            nightly_rate_minor_units=r["rate_minor"],
                            last_cleaned_at=last_cleaned,
                        )
                    )
                    created += 1
                click.echo(
                    f"[ok] inserted {created} new rooms, {len(existing_numbers)} already existed"
                )

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
