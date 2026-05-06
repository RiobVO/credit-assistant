"""E2E: /api/system/health и /api/system/health/history против real Postgres."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from infrastructure.persistence.database import get_session
from infrastructure.persistence.models.system_uptime_day import SystemUptimeDayORM
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


async def test_system_health_returns_services_without_auth(
    api_client: httpx.AsyncClient,
) -> None:
    """Endpoint открыт без JWT — нужен для liveness и pre-auth Settings."""
    resp = await api_client.get("/api/system/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ok", "degraded", "down"}
    assert "checked_at" in body
    # 5 plain-language сервисов (Phase 5 design — см. system.py).
    keys = {svc["key"] for svc in body["services"]}
    assert keys == {
        "search",
        "dossiers_db",
        "soliq_import",
        "pdf_generation",
        "faktura_uz",
    }


async def test_system_health_upserts_today_row(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """При каждом вызове создаётся / обновляется row на сегодня."""
    # Очищаем seed-row из миграции, чтобы проверить чистый INSERT-path.
    await pg_session.execute(
        SystemUptimeDayORM.__table__.delete()
    )
    await pg_session.flush()

    await api_client.get("/api/system/health")

    rows = (
        await pg_session.execute(select(SystemUptimeDayORM))
    ).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.day == datetime.now(tz=UTC).date()
    # Postgres работает (тест проходит) → overall ok или degraded (если WeasyPrint
    # не установлен в test-окружении). 'down' быть не должно.
    assert row.status in {"ok", "degraded"}


async def test_system_health_does_not_create_duplicate_today_row(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Два вызова в один день — один row, last_seen_at обновлён."""
    await pg_session.execute(SystemUptimeDayORM.__table__.delete())
    await pg_session.flush()

    await api_client.get("/api/system/health")
    await api_client.get("/api/system/health")

    rows = (
        await pg_session.execute(select(SystemUptimeDayORM))
    ).scalars().all()
    assert len(rows) == 1


async def test_system_health_history_returns_days_with_first_seen(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """History возвращает реально-известные дни + first_seen_day."""
    # Trigger today's row.
    await api_client.get("/api/system/health")

    resp = await api_client.get("/api/system/health/history?days=30")
    assert resp.status_code == 200
    body = resp.json()
    assert body["first_seen_day"] is not None
    assert isinstance(body["days"], list)
    assert len(body["days"]) >= 1
    # Каждая day-запись имеет валидный status.
    for day in body["days"]:
        assert day["status"] in {"ok", "degraded", "down"}
        assert "day" in day


async def test_system_health_history_clamps_days_to_valid_range(
    api_client: httpx.AsyncClient,
) -> None:
    """days < 1 → 422 (Pydantic validation)."""
    resp = await api_client.get("/api/system/health/history?days=0")
    assert resp.status_code == 422

    resp = await api_client.get("/api/system/health/history?days=999")
    assert resp.status_code == 422
