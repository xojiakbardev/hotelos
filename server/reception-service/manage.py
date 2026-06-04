#!/usr/bin/env python
"""Management CLI for reception-service.

Commands:
  makemigrations <message>   — alembic revision --autogenerate -m "<message>"
  migrate                    — alembic upgrade head
  seedguests [--count N]     — seed N fake guests into available clean rooms (uses Faker)
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



@cli.command()
@click.option("--count", default=10, help="Number of fake guests to seed")
def seedguests(count: int) -> None:
    """Seed random guests into available clean rooms using Faker."""
    from faker import Faker
    import random
    from src.domain.models import Guest, Room
    from src.core.broker import create_redis
    from src.events.publisher import EventPublisher
    from src.events.topics import Channels
    
    fake = Faker("uz_UZ")

    async def _run() -> None:
        async with async_session_factory() as session:
            # 1. Fetch available clean rooms
            stmt = select(Room).where(
                Room.status == "available",
                Room.cleanliness_status == "clean"
            )
            rooms = list((await session.execute(stmt)).scalars().all())
            
            if not rooms:
                click.echo("[skip] Bazada birorta ham toza va bo'sh xona topilmadi. Avval xonalarni yarating.")
                return

            # Pick min(count, len(rooms)) rooms to seed
            target_rooms = random.sample(rooms, min(count, len(rooms)))
            
            # Setup publisher
            redis_client = create_redis()
            publisher = EventPublisher(redis_client, "reception-service")
            
            seeded = 0
            for room in target_rooms:
                async with session.begin():
                    # Generate fake user details
                    first_name = fake.first_name()
                    last_name = fake.last_name()
                    full_name = f"{first_name} {last_name}"
                    
                    # Generate Uz phone format: +99890XXXXXXX
                    phone = f"+99890{random.randint(1000000, 9999999)}"
                    passport = f"{random.choice(['AA', 'AB', 'AD', 'KA'])}{random.randint(1000000, 9999999)}"
                    
                    nights = random.randint(1, 5)
                    checked_in_at = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 12))
                    expected_checkout = checked_in_at + timedelta(days=nights)
                    
                    # Create guest
                    guest = Guest(
                        full_name=full_name,
                        phone=phone,
                        passport_number=passport,
                        room_id=room.id,
                        checked_in_at=checked_in_at,
                        expected_checkout_at=expected_checkout,
                        nightly_rate_locked_minor_units=room.nightly_rate_minor_units,
                        cleaning_preference=random.choice(["morning", "afternoon", "evening"]),
                        do_not_disturb=random.choice([True, False, False, False]),
                    )
                    session.add(guest)
                    
                    # Mark room as occupied
                    room.status = "occupied"
                    room.last_assigned_at = checked_in_at
                    
                    await session.flush()
                    
                    guest_id = str(guest.id)
                    room_id = str(room.id)
                    room_number = room.room_number
                    floor = room.floor
                    room_type = room.room_type
                    
                # Publish check-in event outside transaction (after successful commit)
                await publisher.publish(
                    channel=Channels.GUEST_CHECKED_IN,
                    payload={
                        "guest_id": guest_id,
                        "room_id": room_id,
                        "room_number": room_number,
                        "floor": floor,
                        "room_type": room_type,
                        "full_name": full_name,
                        "checked_in_at": checked_in_at.isoformat(),
                    },
                )
                seeded += 1
                click.echo(f"[ok] room #{room_number} assigned to {full_name} ({phone})")

            # Clean up redis connection
            await redis_client.aclose()
            click.echo(f"Seeding completed. {seeded} guests checked in.")

    asyncio.run(_run())


if __name__ == "__main__":
    cli()

