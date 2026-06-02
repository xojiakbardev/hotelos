"""Alembic env for reception-service. Scoped to the `reception` schema."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.core.config import settings
from src.domain.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata
SCHEMA = settings.service_schema


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and getattr(obj, "schema", None) not in (None, SCHEMA):
        return False
    return True


def do_run_migrations(connection: Connection) -> None:
    # Schema must exist before Alembic creates its version table. Wrap in an
    # explicit transaction so the CREATE SCHEMA commits before the migration
    # transaction starts — otherwise SQLAlchemy 2.0 autobegin leaves it pending
    # and the whole thing rolls back on disconnect.
    with connection.begin():
        connection.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema=SCHEMA,
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


asyncio.run(run_migrations_online())
