"""E2E: /api/system/okved (CA-DS17)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
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


async def test_okved_returns_msb_catalog_without_auth(
    api_client: httpx.AsyncClient,
) -> None:
    """Endpoint открыт без JWT — reference data, не PII."""
    resp = await api_client.get("/api/system/okved")
    assert resp.status_code == 200
    body = resp.json()
    items = body["items"]
    assert isinstance(items, list)
    assert len(items) >= 17  # PDF legacy + frontend MSB union


async def test_okved_items_sorted_by_code_ascending(
    api_client: httpx.AsyncClient,
) -> None:
    """Sorted ascending — стабильный rendering на frontend."""
    resp = await api_client.get("/api/system/okved")
    items = resp.json()["items"]
    codes = [item["code"] for item in items]
    assert codes == sorted(codes)


async def test_okved_each_item_has_localized_labels(
    api_client: httpx.AsyncClient,
) -> None:
    """Каждый item содержит RU+UZ short+full (готов к runtime locale switch)."""
    resp = await api_client.get("/api/system/okved")
    items = resp.json()["items"]
    for item in items:
        assert item["code"]
        assert item["short_ru"]
        assert item["full_ru"]
        assert item["short_uz"]
        assert item["full_uz"]


async def test_okved_includes_known_msb_codes(
    api_client: httpx.AsyncClient,
) -> None:
    """Smoke: знакомые MSB-коды доступны (no-regression при удалении hardcoded dict)."""
    resp = await api_client.get("/api/system/okved")
    codes = {item["code"] for item in resp.json()["items"]}
    expected = {"47.11", "62.01", "46.39", "85.10"}
    assert expected.issubset(codes)
