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


# Default rooms to seed — [room_number, floor, room_type, proximity, price_minor_units]
SEED_ROOMS = [
    # 1-qavat: 101-110
    (101, 1, "single",     "elevator", 20000000),
    (102, 1, "single",     "elevator", 20000000),
    (103, 1, "double",     "elevator", 35000000),
    (104, 1, "double",     "stairs",   35000000),
    (105, 1, "suite",      "elevator", 80000000),
    (106, 1, "accessible", "elevator", 25000000),
    (107, 1, "single",     "stairs",   20000000),
    (108, 1, "double",     "stairs",   35000000),
    (109, 1, "suite",      "stairs",   80000000),
    (110, 1, "single",     "other",    20000000),
    # 2-qavat: 201-210
    (201, 2, "single",     "elevator", 22000000),
    (202, 2, "single",     "elevator", 22000000),
    (203, 2, "double",     "elevator", 38000000),
    (204, 2, "double",     "stairs",   38000000),
    (205, 2, "suite",      "elevator", 90000000),
    (206, 2, "accessible", "elevator", 27000000),
    (207, 2, "double",     "stairs",   38000000),
    (208, 2, "single",     "other",    22000000),
    (209, 2, "suite",      "stairs",   90000000),
    (210, 2, "double",     "elevator", 38000000),
    # 3-qavat: 301-310
    (301, 3, "single",     "elevator", 24000000),
    (302, 3, "double",     "elevator", 40000000),
    (303, 3, "double",     "stairs",   40000000),
    (304, 3, "suite",      "elevator", 95000000),
    (305, 3, "suite",      "stairs",   95000000),
    (306, 3, "single",     "stairs",   24000000),
    (307, 3, "double",     "elevator", 40000000),
    (308, 3, "accessible", "elevator", 28000000),
    (309, 3, "single",     "other",    24000000),
    (310, 3, "double",     "other",    40000000),
]


@cli.command()
def seedrooms() -> None:
    """Seed 30 rooms (3 floors × 10 rooms) if not already present."""
    from src.domain.enums import Cleanliness, RoomStatus
    from src.services.freshness import compute_dynamic_price

    async def _run() -> None:
        async with async_session_factory() as session:
            async with session.begin():
                existing = set(
                    (await session.execute(select(Room.room_number))).scalars().all()
                )
                added = 0
                for num, floor, rtype, prox, price in SEED_ROOMS:
                    if num in existing:
                        continue
                    room = Room(
                        room_number=num,
                        floor=floor,
                        room_type=rtype,
                        proximity=prox,
                        nightly_rate_minor_units=price,
                        cleanliness_status=Cleanliness.CLEAN.value,
                        status=RoomStatus.AVAILABLE.value,
                        freshness_score=1.0,
                        dynamic_price_minor_units=compute_dynamic_price(price, 1.0),
                    )
                    session.add(room)
                    added += 1
        click.echo(f"seeded {added} rooms ({len(SEED_ROOMS) - added} already present)")

    asyncio.run(_run())



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
            
            # Commit the read transaction so we can start fresh ones
            await session.commit()
            
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
                    
                    # Generate credentials
                    import uuid
                    from src.services.credential_generator import generate_guest_pin, hash_pin
                    auth_user_id = uuid.uuid4()
                    guest_pin = generate_guest_pin()
                    pin_hash = hash_pin(guest_pin)
                    
                    # Create guest with auth_user_id
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
                        auth_user_id=auth_user_id,
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
                    
                # Publish events outside transaction
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
                # Publish credential event so auth-service creates guest user
                await publisher.publish(
                    channel=Channels.GUEST_CREDENTIAL_CREATED,
                    payload={
                        "auth_user_id": str(auth_user_id),
                        "phone": phone,
                        "password_hash": pin_hash,
                        "full_name": full_name,
                        "guest_id": guest_id,
                        "room_id": room_id,
                        "room_number": room_number,
                    },
                )
                seeded += 1
                click.echo(f"[ok] room #{room_number} assigned to {full_name} ({phone}) PIN={guest_pin}")

            # Clean up redis connection
            await redis_client.aclose()
            click.echo(f"Seeding completed. {seeded} guests checked in.")

    asyncio.run(_run())


if __name__ == "__main__":
    cli()

