"""E2E: GET /api/bank/stats/today — daily aggregation для live-strip."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.dossier_record import DossierRecord
from config.settings import Settings
from infrastructure.auth.password_hasher import PasswordHasher
from infrastructure.persistence.database import get_session
from infrastructure.persistence.models.analyst import AnalystORM
from infrastructure.persistence.repositories.borrower_repository import (
    SqlAlchemyBorrowerRepository,
)
from infrastructure.persistence.repositories.borrower_snapshot_repository import (
    SqlAlchemyBorrowerSnapshotRepository,
)
from infrastructure.persistence.repositories.dossier_repository import (
    SqlAlchemyDossierRepository,
)
from interfaces.api.app import create_app
from interfaces.api.bank.dependencies import get_jwt_service, get_password_hasher
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service
from tests.fixtures.synthetic_borrowers import clean_borrower

pytestmark = pytest.mark.integration

EMAIL = "analyst@bank.uz"
PASSWORD = "S3cret!"


async def _seed_analyst(session: AsyncSession) -> AnalystORM:
    hasher = PasswordHasher(rounds=4)
    orm = AnalystORM(
        email=EMAIL,
        password_hash=hasher.hash(PASSWORD),
        full_name="Иванов И.И.",
        role="analyst",
        is_active=True,
    )
    session.add(orm)
    await session.flush()
    return orm


async def _login(client: httpx.AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def api_client(pg_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    get_rule_registry.cache_clear()
    get_scoring_service.cache_clear()
    get_jwt_service.cache_clear()
    get_password_hasher.cache_clear()

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield pg_session

    def _fast_hasher() -> PasswordHasher:
        return PasswordHasher(rounds=4)

    app = create_app(Settings(app_mode="bank"))
    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_password_hasher] = _fast_hasher
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _record(recommendation: str = "approve", score: int = 10) -> DossierRecord:
    return DossierRecord(
        score=score,
        recommendation=recommendation,
        severity_breakdown={},
        red_flags=(),
        rules_version="v1",
        rules_evaluated=19,
    )


async def test_stats_empty_when_no_dossiers_today(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)
    headers = await _login(api_client)

    resp = await api_client.get("/api/bank/stats/today", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "collected_today": 0,
        "approved_pct": None,
        "in_review_today": 0,
    }


async def test_stats_aggregates_today_dossiers(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """3 today: 2 approve + 1 review. approved_pct = round(2/3*100) = 67%."""
    analyst = await _seed_analyst(pg_session)
    snapshot = clean_borrower()
    borrower_id = await SqlAlchemyBorrowerRepository(pg_session).upsert(snapshot.borrower)
    snapshot_id = await SqlAlchemyBorrowerSnapshotRepository(pg_session).save(
        snapshot, borrower_id
    )
    repo = SqlAlchemyDossierRepository(pg_session)
    aid = analyst.id
    await repo.save(
        _record("approve"), snapshot_id, "BR-2026-D001",
        source_mode="bank", created_by_analyst_id=aid,
    )
    await repo.save(
        _record("approve"), snapshot_id, "BR-2026-D002",
        source_mode="bank", created_by_analyst_id=aid,
    )
    await repo.save(
        _record("review"), snapshot_id, "BR-2026-D003",
        source_mode="bank", created_by_analyst_id=aid,
    )

    headers = await _login(api_client)
    resp = await api_client.get("/api/bank/stats/today", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["collected_today"] == 3
    assert body["approved_pct"] == 67
    assert body["in_review_today"] == 1


async def test_stats_ignores_accountant_mode_dossiers(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Только bank-mode идёт в счётчик."""
    await _seed_analyst(pg_session)
    snapshot = clean_borrower()
    borrower_id = await SqlAlchemyBorrowerRepository(pg_session).upsert(snapshot.borrower)
    snapshot_id = await SqlAlchemyBorrowerSnapshotRepository(pg_session).save(
        snapshot, borrower_id
    )
    repo = SqlAlchemyDossierRepository(pg_session)
    await repo.save(_record("approve"), snapshot_id, "BR-2026-D004", source_mode="accountant")
    await repo.save(_record("approve"), snapshot_id, "BR-2026-D005", source_mode="accountant")

    headers = await _login(api_client)
    resp = await api_client.get("/api/bank/stats/today", headers=headers)
    assert resp.json()["collected_today"] == 0


async def test_stats_repo_filters_by_date(
    pg_session: AsyncSession,
) -> None:
    """Unit-проверка repo.get_bank_daily_stats — отдельная дата filter."""
    snapshot = clean_borrower()
    borrower_id = await SqlAlchemyBorrowerRepository(pg_session).upsert(snapshot.borrower)
    snapshot_id = await SqlAlchemyBorrowerSnapshotRepository(pg_session).save(
        snapshot, borrower_id
    )
    repo = SqlAlchemyDossierRepository(pg_session)
    # Today's dossier
    await repo.save(_record("approve"), snapshot_id, "BR-2026-D006", source_mode="bank")
    # «Yesterday's» — нельзя установить created_at напрямую через save, но мы
    # проверяем что repo query с date.today() видит todays-only автоматически.
    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)

    today_stats = await repo.get_bank_daily_stats(today)
    yesterday_stats = await repo.get_bank_daily_stats(yesterday)

    assert today_stats.collected_today >= 1
    # Для yesterday не должно быть наших dossiers (created_at = now()).
    assert yesterday_stats.collected_today == 0


async def test_stats_requires_auth(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.get("/api/bank/stats/today")
    assert resp.status_code == 401
