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
    ("Espresso",       "drinks",  350,  3),
    ("Cappuccino",     "drinks",  500,  5),
    ("Fresh juice",    "drinks",  600,  4),
    ("Club sandwich",  "mains",  1200, 12),
    ("Margherita pizza","mains", 1500, 18),
    ("Caesar salad",   "mains",   900, 10),
    ("Cheesecake",     "desserts",700,  5),
    ("Ice cream",      "desserts",400,  3),
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
