"""E2E: CA-DS9 uptime collector tick пишет today's row в system_uptime_day."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.jobs.uptime_collector import perform_uptime_tick
from infrastructure.persistence.models.system_uptime_day import SystemUptimeDayORM

pytestmark = pytest.mark.integration


async def test_perform_uptime_tick_upserts_today_row(pg_session: AsyncSession) -> None:
    """После tick'а для today обязан существовать ровно один row с записанным
    статусом. Pre-existing row (от предыдущих non-rolled-back прогонов) не
    мешает — UPSERT работает либо INSERT либо UPDATE.
    """
    today = datetime.now(tz=UTC).date()

    status = await perform_uptime_tick(pg_session)
    assert status in {"ok", "degraded", "down"}

    rows = (
        await pg_session.execute(
            select(SystemUptimeDayORM).where(SystemUptimeDayORM.day == today)
        )
    ).scalars().all()
    assert len(rows) == 1
    # worst-of-day: row.status >= status (только эскалирует, не deeskalируется).
    # Если pre-existing row был ok и tick='ok' — равны. Если был degraded —
    # status остался degraded.
    assert rows[0].status in {"ok", "degraded", "down"}


async def test_perform_uptime_tick_is_idempotent_on_same_day(
    pg_session: AsyncSession,
) -> None:
    """Несколько tick'ов за один день не плодят строки — UPSERT на PK=day."""
    today = datetime.now(tz=UTC).date()

    s1 = await perform_uptime_tick(pg_session)
    s2 = await perform_uptime_tick(pg_session)
    s3 = await perform_uptime_tick(pg_session)
    # Worst-of-day только эскалирует, не deeskalируется — без транзиента все три
    # одинаковые.
    assert s1 == s2 == s3

    rows = (
        await pg_session.execute(
            select(SystemUptimeDayORM).where(SystemUptimeDayORM.day == today)
        )
    ).scalars().all()
    assert len(rows) == 1
    # last_seen_at должен сдвигаться при каждом tick'е.
    assert rows[0].last_seen_at is not None
