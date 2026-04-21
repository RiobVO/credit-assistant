"""Фикстуры для integration-тестов поверх real Postgres из testcontainers.

Архитектура:
* `pg_container` — session-scope: один контейнер на весь run.
* `pg_engine` — session-scope: AsyncEngine + применённая миграция Alembic.
* `pg_session` — function-scope: outer transaction + savepoint, rollback на teardown
  откатывает всё, что тест успел записать. Изолирует тесты без drop/recreate схемы.

Авто-skip всего пакета, если Docker недоступен — у тестов хорошее напоминание
«запусти Docker Desktop» и suite не падает в чёрный TimeoutError.

Windows + asyncpg: дефолтный ProactorEventLoop рвёт коннекты на handshake.
``WindowsSelectorEventLoopPolicy`` ставится при импорте этого модуля — до того,
как pytest-asyncio создаст свой loop.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Импорт testcontainers поднимет docker SDK — отдельной проверки не нужно.
try:
    from testcontainers.postgres import PostgresContainer  # type: ignore[import-untyped]
except ImportError as exc:  # pragma: no cover - environment-dependent
    pytest.skip(
        f"testcontainers[postgres] не установлен: {exc}",
        allow_module_level=True,
    )


def _docker_alive() -> tuple[bool, str]:
    """Проверка, доступен ли Docker daemon. Без неё PostgresContainer.start
    висит в внутренних таймаутах — лучше дать понятный skip-reason сразу.
    """
    try:
        import docker

        client = docker.from_env()
        client.ping()
    except Exception as e:  # любая ошибка Docker'а — валидный повод для skip
        return False, str(e)
    return True, ""


_DOCKER_OK, _DOCKER_ERR = _docker_alive()
if not _DOCKER_OK:
    pytest.skip(
        f"Docker daemon недоступен — integration тесты пропущены: {_DOCKER_ERR}",
        allow_module_level=True,
    )


def _to_async_url(sync_url: str) -> str:
    """testcontainers отдаёт URL под psycopg2 (`postgresql+psycopg2://`)
    или чистый `postgresql://`; для asyncpg нужен другой драйвер.
    """
    for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://", "postgresql://"):
        if sync_url.startswith(prefix):
            return "postgresql+asyncpg://" + sync_url.removeprefix(prefix)
    raise ValueError(f"Неожиданный формат URL: {sync_url}")


@pytest.fixture(scope="session")
def pg_container() -> Iterator[PostgresContainer]:
    """Postgres 16 на всю тест-сессию. Cold start ~5-15s на Windows + Docker Desktop."""
    with PostgresContainer("postgres:16-alpine") as c:
        yield c


@pytest.fixture(scope="session")
def pg_async_url(pg_container: PostgresContainer) -> str:
    return _to_async_url(pg_container.get_connection_url())


@pytest.fixture(scope="session")
def _migrated_db(pg_async_url: str) -> Iterator[str]:
    """Применяет alembic upgrade head к контейнеру.

    Через env-переменную DATABASE_URL: ``Settings`` читает её, ``env.py`` Alembic
    использует тот же ``Settings.database_url``. lru_cache настроек чистится
    до и после, чтобы не утянуть тестовый URL в другие тесты процесса.
    """
    from alembic import command
    from alembic.config import Config

    from config.settings import get_settings

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    alembic_ini = os.path.join(project_root, "alembic.ini")

    prev_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = pg_async_url
    get_settings.cache_clear()

    cfg = Config(alembic_ini)
    cfg.set_main_option("script_location", "src/infrastructure/persistence/migrations")
    command.upgrade(cfg, "head")

    try:
        yield pg_async_url
    finally:
        if prev_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev_url
        get_settings.cache_clear()


@pytest_asyncio.fixture
async def pg_engine(_migrated_db: str) -> AsyncIterator[AsyncEngine]:
    """Async engine, function-scope. pytest-asyncio закрывает loop после каждого
    теста; держать engine session-scope = ловить «Event loop is closed» при
    teardown asyncpg-коннекций. Контейнер и миграция остаются session-scope —
    создание engine'а само по себе дешёвое (~10ms).
    """
    from infrastructure.persistence.database import _json_serializer

    engine = create_async_engine(
        _migrated_db,
        future=True,
        json_serializer=_json_serializer,
    )
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def pg_session(pg_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Outer-transaction + savepoint, rollback в teardown.

    Repos внутри теста вольны делать `flush()` / `commit()` — `commit()` коммитит
    nested savepoint, не основную транзакцию. После теста основная транзакция
    откатывается, и БД остаётся в исходном состоянии.
    """
    async with pg_engine.connect() as conn:
        outer_tx = await conn.begin()
        # Сессия привязана к существующему connection — join_transaction_mode гарантирует,
        # что её внутренние commit/rollback работают только с savepoint, не с outer_tx.
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await outer_tx.rollback()
