#!/usr/bin/env python
"""Django-style management CLI for auth-service.

Commands:
  makemigrations <message>   — alembic revision --autogenerate -m "<message>"
  migrate                    — alembic upgrade head
  createmanager              — prompt for phone+password, create a manager user
  seedusers                  — idempotently seed one demo user per role
"""

from __future__ import annotations

import asyncio
import subprocess
import sys

import click

from src.core.config import settings
from src.core.db import async_session_factory
from src.core.security.hash import hash_password
from src.domain.enums import UserRole
from src.infra.repositories.permission_repository import PermissionRepository
from src.infra.repositories.user_repository import UserRepository


@click.group()
def cli() -> None:
    """auth-service management commands."""


@cli.command()
@click.argument("message")
def makemigrations(message: str) -> None:
    """Generate a new Alembic revision from model changes."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", message],
        capture_output=True,
        text=True,
    )
    click.echo(result.stdout)
    if result.returncode != 0:
        click.echo(result.stderr, err=True)
        raise click.Abort()
    for line in result.stdout.splitlines():
        if "Generating " in line:
            click.echo(f"Created: {line.split('Generating ')[1].rstrip(' ...')}")
            break


@cli.command()
def migrate() -> None:
    """Apply pending Alembic migrations."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], capture_output=False
    )
    if result.returncode != 0:
        raise click.Abort()


async def _create_user(
    phone: str, password: str, role: UserRole, full_name: str | None = None
) -> tuple[bool, str]:
    """Returns (created, message). Idempotent on phone."""
    async with async_session_factory() as session:
        repo = UserRepository(session)
        if await repo.get_by_phone(phone) is not None:
            return False, f"already exists: {phone}"
        user = await repo.create(
            phone=phone,
            password_hash=hash_password(password),
            role=role,
            full_name=full_name,
        )
        await PermissionRepository(session).create_default_entries_for_user(user.id, role)
        await session.commit()
        return True, f"created {role.value}: {phone}"


@cli.command()
@click.option("--phone", prompt="Phone", help="Phone number of the manager user")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Password for the manager user",
)
@click.option("--full-name", default=None, help="Optional display name")
def createmanager(phone: str, password: str, full_name: str | None) -> None:
    """Create a top-tier manager user."""
    created, msg = asyncio.run(_create_user(phone, password, UserRole.MANAGER, full_name))
    click.echo(("[ok] " if created else "[skip] ") + msg)


@cli.command()
def seedusers() -> None:
    """Seed one demo user per role using credentials from .env."""
    seeds = [
        (settings.seed_manager_phone, settings.seed_manager_password, UserRole.MANAGER, "Demo Manager"),
        (settings.seed_reception_phone, settings.seed_reception_password, UserRole.RECEPTION, "Demo Reception"),
        (settings.seed_technician_phone, settings.seed_technician_password, UserRole.TECHNICIAN, "Demo Technician"),
        (settings.seed_cleaner_phone, settings.seed_cleaner_password, UserRole.CLEANER, "Demo Cleaner"),
    ]

    async def _run() -> None:
        for phone, pw, role, name in seeds:
            created, msg = await _create_user(phone, pw, role, name)
            click.echo(("[ok] " if created else "[skip] ") + msg)

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
