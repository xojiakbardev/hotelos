#!/usr/bin/env python
"""Management CLI for room-service.

Commands:
  makemigrations <message>   — alembic revision --autogenerate -m "<message>"
  migrate                    — alembic upgrade head
  seedmenu                   — idempotently seed a baseline kitchen menu
"""

from __future__ import annotations

import asyncio
import subprocess
import sys

import click

# Default catalogue inserted by `seedmenu`. Prices are minor units
# (so USD cents / UZS tiyin — driven by whatever the deployment uses).
SEED_MENU = [
    # (name, category, price_minor_units, prep_minutes)
    # Ichimliklar
    ("Espresso",           "drinks",    1500000,  3),
    ("Cappuccino",         "drinks",    2000000,  5),
    ("Limonad",            "drinks",    1800000,  4),
    ("Mineral suv",        "drinks",     800000,  1),
    ("Choy (qora)",        "drinks",     500000,  3),
    # Nonushta
    ("Tuxum va non",       "breakfast", 2500000,  8),
    ("Omlet",              "breakfast", 3000000, 10),
    ("Blinchik",           "breakfast", 2800000,  8),
    # Asosiy taomlar
    ("Palov",              "food",      4500000, 25),
    ("Lag'mon",            "food",      3500000, 20),
    ("Shashlik",           "food",      5000000, 20),
    ("Manti",              "food",      3500000, 30),
    ("Somsa",              "food",      1500000, 15),
    ("Sezar salat",        "food",      3000000, 10),
    # Gazaklar
    ("Chips",              "snacks",    1000000,  2),
    ("Yong'oq aralashmasi","snacks",   1500000,  2),
    # Shirinliklar
    ("Tiramisu",           "dessert",   3500000,  5),
    ("Muzqaymoq",          "dessert",   2000000,  3),
    ("Cheesecake",         "dessert",   3000000,  5),
]


@click.group()
def cli() -> None:
    """room-service management commands."""


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


@cli.command()
def seedmenu() -> None:
    """Insert SEED_MENU rows that don't already exist (idempotent by name)."""

    async def _run() -> None:
        from src.core.db import async_session_factory
        from src.infra.repositories.menu_repository import MenuRepository
        from sqlalchemy import select
        from src.domain.models import MenuItem

        async with async_session_factory() as session:
            async with session.begin():
                existing_names = set(
                    (await session.execute(select(MenuItem.name))).scalars().all()
                )
                repo = MenuRepository(session)
                added = 0
                for name, category, price, prep in SEED_MENU:
                    if name in existing_names:
                        continue
                    await repo.create(
                        name=name,
                        category=category,
                        price_minor_units=price,
                        prep_minutes=prep,
                        is_available=True,
                    )
                    added += 1
        click.echo(f"seeded {added} new menu items ({len(SEED_MENU) - added} already present)")

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
