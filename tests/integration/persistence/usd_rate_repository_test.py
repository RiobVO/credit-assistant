"""Integration test SqlAlchemyUsdRateRepository — testcontainers Postgres (T0.2)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.exchange_rate import UsdUzsRate
from infrastructure.persistence.repositories.usd_rate_repository import (
    SqlAlchemyUsdRateRepository,
)

pytestmark = pytest.mark.integration


async def test_save_and_get_for_date_roundtrip(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyUsdRateRepository(pg_session)
    today = date(2026, 5, 17)
    rate = UsdUzsRate(rate=Decimal("12575.36"), asof=today, source="cbu_live")
    await repo.save(
        rate=rate,
        raw_response={"Rate": "12575.36"},
        fetched_at=datetime.now(tz=UTC),
        nominal=1,
    )
    got = await repo.get_for_date(today)
    assert got is not None
    assert got.rate == Decimal("12575.3600")
    assert got.asof == today
    assert got.source == "cbu_live"


async def test_get_for_date_returns_none_when_absent(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyUsdRateRepository(pg_session)
    got = await repo.get_for_date(date(1999, 1, 1))
    assert got is None


async def test_get_latest_returns_most_recent_date(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyUsdRateRepository(pg_session)
    for d, r in [
        (date(2026, 5, 10), Decimal("12500")),
        (date(2026, 5, 17), Decimal("12575")),
        (date(2026, 5, 15), Decimal("12550")),
    ]:
        await repo.save(
            rate=UsdUzsRate(rate=r, asof=d, source="cbu_live"),
            raw_response=None,
            fetched_at=datetime.now(tz=UTC),
        )
    latest = await repo.get_latest()
    assert latest is not None
    assert latest.asof == date(2026, 5, 17)
    assert latest.rate == Decimal("12575.0000")


async def test_save_on_conflict_does_nothing(pg_session: AsyncSession) -> None:
    """Конкурентные save на ту же дату — второй no-op, первый winner."""
    repo = SqlAlchemyUsdRateRepository(pg_session)
    target = date(2026, 5, 17)
    await repo.save(
        rate=UsdUzsRate(rate=Decimal("12500"), asof=target, source="cbu_live"),
        raw_response={"first": True},
        fetched_at=datetime.now(tz=UTC),
    )
    # Конкурентный save — параметры другие, но date PK уже занят.
    await repo.save(
        rate=UsdUzsRate(rate=Decimal("99999"), asof=target, source="env"),
        raw_response={"second": True},
        fetched_at=datetime.now(tz=UTC),
    )
    got = await repo.get_for_date(target)
    # Первый winner — second save не перетёр.
    assert got is not None
    assert got.rate == Decimal("12500.0000")
    assert got.source == "cbu_live"


async def test_get_latest_returns_none_on_empty_table(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyUsdRateRepository(pg_session)
    assert await repo.get_latest() is None
