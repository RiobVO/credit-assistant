"""Async SQLAlchemy engine + session factory.

Единая точка инициализации БД для приложения и Alembic.
Engine ленив (создаётся при первом обращении), чтобы импорт модуля
не падал на машинах без поднятого Postgres (например, в unit-тестах domain).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config.settings import get_settings


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей persistence слоя."""


def _json_default(obj: Any) -> Any:
    """JSON encoder fallback для JSONB-колонок (snapshot.payload, dossier.red_flags).

    * Decimal → str: сохраняем precision (float её бы потерял).
    * datetime/date → isoformat: rule evidence бывает с временными метками;
      обратная конверсия — на стороне mapper'а конкретного потребителя.
    """
    if isinstance(obj, Decimal):
        return str(obj)
    # ВАЖНО: datetime — подкласс date, проверяем сначала его (isoformat для обоих).
    if isinstance(obj, datetime | date):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _json_serializer(value: Any) -> str:
    return json.dumps(value, default=_json_default, ensure_ascii=False)


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Возвращает singleton async engine.

    Строка подключения берётся из `Settings.database_url`. Engine создаётся
    один раз на процесс — `dispose_engine()` нужен для тестов и graceful shutdown.
    """
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            future=True,
            pool_pre_ping=True,
            json_serializer=_json_serializer,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Singleton фабрика сессий, привязанная к глобальному engine."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: одна сессия на запрос с авто-commit/rollback.

    Транзакция начинается на входе, коммитится при штатном выходе,
    откатывается при любом исключении. Хэндлеру не нужно явно вызывать commit.
    """
    factory = get_session_factory()
    async with factory() as session, session.begin():
        yield session


async def dispose_engine() -> None:
    """Закрывает engine (graceful shutdown / pytest teardown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
