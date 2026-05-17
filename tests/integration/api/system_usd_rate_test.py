"""E2E: /api/system/usd-rate — service-based fallback chain (T0.2).

После T0.2 endpoint больше не использует singleton ``default_usd_uzs_rate``.
Вместо singleton — ``UsdRateService`` с fallback chain: env → DB today →
CBU live → DB latest → JSON bootstrap.

В этих тестах CBU client мокается через monkeypatch — реальный сетевой
вызов в тестах недопустим. Все ветки fallback chain проверяются:
- env override → source="env"
- CBU live fetch + save в DB → source="cbu_live"
- env пустой + CBU down + DB пустая → JSON bootstrap → source="manual"
- env override через `USD_UZS_RATE` env var
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from infrastructure.external.cbu_client import CbuFetchError, CbuRate
from infrastructure.persistence.database import get_session
from interfaces.api.app import create_app
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def api_client(pg_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    get_rule_registry.cache_clear()
    get_scoring_service.cache_clear()

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield pg_session

    app = create_app(Settings(app_mode="bank"))
    app.dependency_overrides[get_session] = _override_get_session
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


async def test_cbu_live_fetch_populates_db_and_returns_cbu_live_source(
    api_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Без env, DB пустая → service fetch'ит CBU, save, отдаёт source=cbu_live."""
    monkeypatch.delenv("USD_UZS_RATE", raising=False)
    today = datetime.now(tz=UTC).date()

    async def fake_fetch() -> CbuRate:
        return CbuRate(
            rate=Decimal("12575.36"),
            asof=today,
            nominal=1,
            raw={"Rate": "12575.36", "Date": today.strftime("%d.%m.%Y")},
        )

    monkeypatch.setattr(
        "application.services.usd_rate_service.fetch_usd_rate", fake_fetch
    )

    resp = await api_client.get("/api/system/usd-rate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "cbu_live"
    assert Decimal(body["rate"]) == Decimal("12575.36")


async def test_env_override_takes_highest_priority(
    api_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USD_UZS_RATE", "13500")
    resp = await api_client.get("/api/system/usd-rate")
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["rate"]) == Decimal("13500")
    assert body["source"] == "env"


async def test_json_bootstrap_when_cbu_down_and_db_empty(
    api_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("USD_UZS_RATE", raising=False)

    async def failing_fetch() -> CbuRate:
        raise CbuFetchError("CBU unavailable in test")

    monkeypatch.setattr(
        "application.services.usd_rate_service.fetch_usd_rate", failing_fetch
    )

    resp = await api_client.get("/api/system/usd-rate")
    assert resp.status_code == 200
    body = resp.json()
    # JSON bootstrap из config/exchange/rates.json
    assert body["source"] == "manual"
    assert Decimal(body["rate"]) > 0


async def test_db_cached_used_when_cbu_down_and_db_has_yesterday(
    api_client: httpx.AsyncClient,
    pg_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Сначала seed yesterday-row → CBU down → fallback на db_cached."""
    monkeypatch.delenv("USD_UZS_RATE", raising=False)

    async def failing_fetch() -> CbuRate:
        raise CbuFetchError("CBU unavailable")

    monkeypatch.setattr(
        "application.services.usd_rate_service.fetch_usd_rate", failing_fetch
    )

    # Seed yesterday-row напрямую в БД.
    from infrastructure.persistence.models.usd_uzs_rate import UsdUzsRateORM

    yesterday = date(2026, 5, 16)
    pg_session.add(
        UsdUzsRateORM(
            date=yesterday,
            rate=Decimal("12500.0000"),
            nominal=1,
            source="cbu_live",
            fetched_at=datetime(2026, 5, 16, 10, 0, tzinfo=UTC),
            raw_response={"Rate": "12500.0"},
        )
    )
    await pg_session.flush()

    resp = await api_client.get("/api/system/usd-rate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "db_cached"
    assert Decimal(body["rate"]) == Decimal("12500.0000")
    assert body["asof"] == "2026-05-16"


async def test_endpoint_open_without_auth(
    api_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Endpoint публичный — reference data, никаких PII."""

    async def fake_fetch() -> CbuRate:
        return CbuRate(
            rate=Decimal("12575"),
            asof=datetime.now(tz=UTC).date(),
            nominal=1,
            raw={},
        )

    monkeypatch.setattr(
        "application.services.usd_rate_service.fetch_usd_rate", fake_fetch
    )
    resp = await api_client.get("/api/system/usd-rate")
    assert resp.status_code == 200
    assert "rate" in resp.json()
