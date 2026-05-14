"""Background-task: каждую минуту пишет worst-of-day status в system_uptime_day.

CA-DS9 — до этого collector жил только в `GET /api/system/health`: row
обновлялся только когда аналитик открывал /settings → О системе или k8s
liveness-probe пинговал. На bank-mode с одним user'ом, который заходит
редко, многие дни оставались пустыми → uptime-calendar показывал серые
квадраты → счётчик «N дней без сбоев» становился ложью.

Решение — внутрипроцессный asyncio-loop поверх FastAPI lifespan:
* `uptime_tick` делает один цикл: probe Postgres, probe WeasyPrint, worst-of,
  UPSERT today. Без HTTP — напрямую через session_factory.
* `uptime_collector_loop` крутится с интервалом `interval_seconds` (default
  60s), пока его не отменят. Безопасен к `CancelledError`.

Почему не ARQ:
* Один процесс api, нет очереди jobs, задача < 100ms — overkill.
* Redis у нас есть, но добавление worker-container = compose-сервис +
  Dockerfile target + monitor-настройки. Скоуп CA-DS9 — 30 минут.

Multi-worker safety:
* Если когда-нибудь поднимем `uvicorn --workers N>1`, каждый процесс
  запустит свой loop. UPSERT идемпотентен и worst-of-day только эскалирует
  (см. SqlAlchemySystemUptimeRepository), так что коллизии не страшны —
  просто лишние writes. До этого момента — single process.

Synchronized with `interfaces/api/shared/system.py` — две probe-функции
дублируются намеренно (избегаем рефакторинг shared/system.py в скоупе
CA-DS9). Будущий refactor: вынести в `infrastructure/health/probes.py`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.persistence.repositories.system_uptime_repository import (
    SqlAlchemySystemUptimeRepository,
)

logger = logging.getLogger(__name__)


_OVERALL_PRIORITY = {"ok": 0, "degraded": 1, "down": 2}


def _check_weasyprint() -> bool:
    """Mirrored с `shared/system._check_weasyprint`. См. модульный docstring."""
    try:
        import weasyprint  # noqa: F401

        return True
    except Exception:
        return False


async def _check_postgres(session: AsyncSession) -> bool:
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _worst(*statuses: str) -> str:
    if not statuses:
        return "ok"
    return max(statuses, key=lambda s: _OVERALL_PRIORITY.get(s, 0))


async def perform_uptime_tick(session: AsyncSession) -> str:
    """Один цикл collector'а в рамках уже открытой сессии. Возвращает
    worst-of-day status, который был записан.

    Выделен из `uptime_tick`, чтобы integration-тест мог передать
    pg_session (savepoint-rollback фикстура) без открытия своей транзакции.
    """
    postgres_ok = await _check_postgres(session)
    postgres_status = "ok" if postgres_ok else "down"
    pdf_status = "ok" if _check_weasyprint() else "degraded"

    overall = _worst(postgres_status, pdf_status)

    repo = SqlAlchemySystemUptimeRepository(session)
    await repo.upsert_today(status=overall, now=datetime.now(tz=UTC))
    return overall


async def uptime_tick(session_factory: async_sessionmaker[AsyncSession]) -> str:
    """Production wrapper над `perform_uptime_tick`: открывает свежую сессию,
    обёрнутую в транзакцию. Long-running task'у нельзя держать одну сессию
    между итерациями — pool_pre_ping не спасёт от stale state.
    """
    async with session_factory() as session, session.begin():
        return await perform_uptime_tick(session)


async def uptime_collector_loop(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    interval_seconds: float = 60.0,
) -> None:
    """Бесконечный loop: tick → sleep → tick. Отменяется через task.cancel().

    Ошибки одного tick'а не валят loop — логируем и продолжаем. Иначе один
    transient DB-glitch остановит сбор на весь срок жизни процесса.
    """
    logger.info("uptime_collector_started", extra={"interval_s": interval_seconds})
    try:
        while True:
            try:
                status = await uptime_tick(session_factory)
                logger.debug("uptime_tick_ok", extra={"status": status})
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("uptime_tick_failed")
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("uptime_collector_stopped")
        raise
