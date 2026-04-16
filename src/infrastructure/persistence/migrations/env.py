"""Alembic env: async вариант через `async_engine_from_config` + `run_sync`.

URL берётся из `Settings.database_url` (asyncpg). `target_metadata` — это
`Base.metadata` из `infrastructure.persistence.database`. По мере появления
ORM-моделей их импорт сюда добавляется, чтобы autogenerate видел все таблицы.
"""

from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from config.settings import get_settings
from infrastructure.persistence.database import Base

# Windows: asyncpg несовместим с дефолтным ProactorEventLoop —
# соединение рвётся в момент хендшейка. Переключаем policy до asyncio.run.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Alembic Config object — предоставляет доступ к alembic.ini.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Подаём URL из Settings, не из alembic.ini — единый источник правды.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# Метаданные всех ORM-моделей. Модели импортируются здесь (а не в database.py),
# чтобы избежать циклических импортов и держать database.py минимальным.
# 2.5.2: импорты BorrowerORM/SnapshotORM/DossierORM/DraftORM добавятся ниже.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline-режим: генерирует SQL без подключения к БД."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Online-режим: подключается к БД через async engine, миграции — через run_sync."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
