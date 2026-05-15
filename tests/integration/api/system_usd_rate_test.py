"""E2E: /api/system/usd-rate (CA-DS24)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from infrastructure.catalog.exchange_rates import default_usd_uzs_rate
from infrastructure.persistence.database import get_session
from interfaces.api.app import create_app
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _clear_usd_rate_singleton() -> Iterator[None]:
    """USD rate теперь singleton (mirror OKVED). В тестах с monkeypatch
    env-override это даёт false positives — clear до/после."""
    default_usd_uzs_rate.cache_clear()
    yield
    default_usd_uzs_rate.cache_clear()


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


async def test_usd_rate_returns_default_from_file(
    api_client: httpx.AsyncClient,
) -> None:
    """Без env override — source=manual, rate из config/exchange/rates.json."""
    resp = await api_client.get("/api/system/usd-rate")
    assert resp.status_code == 200
    body = resp.json()
    # rate приходит строкой — Decimal через JSON. Проверяем парсимость.
    assert Decimal(body["rate"]) > 0
    assert body["source"] == "manual"
    # asof — ISO YYYY-MM-DD.
    assert len(body["asof"]) == 10
    assert body["asof"][4] == "-" and body["asof"][7] == "-"


async def test_usd_rate_env_override(
    api_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USD_UZS_RATE", "13500")
    resp = await api_client.get("/api/system/usd-rate")
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["rate"]) == Decimal("13500")
    assert body["source"] == "env"


async def test_usd_rate_open_without_auth(
    api_client: httpx.AsyncClient,
) -> None:
    """Endpoint публичный — reference data."""
    resp = await api_client.get("/api/system/usd-rate")
    assert resp.status_code == 200
    assert "rate" in resp.json()
