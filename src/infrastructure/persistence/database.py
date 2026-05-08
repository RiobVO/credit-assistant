"""Async SQLAlchemy engine + session factory.

Единая точка инициализации БД для приложения и Alembic.
Engine ленив (создаётся при первом обращении), чтобы импорт модуля
не падал на машинах без поднятого Postgres (например, в unit-тестах domain).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

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
    """FastAPI dependency: одна сессия на запрос с автокоммитом транзакции."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def dispose_engine() -> None:
    """Закрывает engine (graceful shutdown / pytest teardown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
