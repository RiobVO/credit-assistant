"""E2E: GET /api/bank/borrowers/search — 3 ветки + audit + auth-required."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.dossier_record import DossierRecord
from config.settings import Settings
from infrastructure.auth.password_hasher import PasswordHasher
from infrastructure.persistence.database import get_session
from infrastructure.persistence.models.analyst import AnalystORM
from infrastructure.persistence.models.audit_log import AuditLogORM
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
    body = resp.json()
    return {"Authorization": f"Bearer {body['access_token']}"}


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


def _record(score: int = 25) -> DossierRecord:
    return DossierRecord(
        score=score,
        recommendation="review",
        severity_breakdown={"low": 1, "medium": 1},
        red_flags=(),
        rules_version="v1",
        rules_evaluated=17,
    )


async def test_search_returns_not_found_for_unknown_inn(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)
    headers = await _login(api_client)

    resp = await api_client.get(
        "/api/bank/borrowers/search?inn=999999999", headers=headers
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert body["borrower_name"] is None
    assert body["dossier_id"] is None


async def test_search_returns_borrower_without_dossier(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Borrower есть в БД, но bank-mode досье ещё нет."""
    await _seed_analyst(pg_session)
    snapshot = clean_borrower()
    await SqlAlchemyBorrowerRepository(pg_session).upsert(snapshot.borrower)

    headers = await _login(api_client)
    inn = snapshot.borrower.inn.value
    resp = await api_client.get(
        f"/api/bank/borrowers/search?inn={inn}", headers=headers
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert body["borrower_name"] == snapshot.borrower.name
    assert body["dossier_id"] is None
    assert body["score"] is None


async def test_search_returns_latest_bank_dossier(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Среди нескольких bank-mode досье берётся самое свежее. Accountant-досье игнорируются."""
    analyst = await _seed_analyst(pg_session)
    snapshot = clean_borrower()
    borrower_id = await SqlAlchemyBorrowerRepository(pg_session).upsert(snapshot.borrower)
    snapshot_id = await SqlAlchemyBorrowerSnapshotRepository(pg_session).save(
        snapshot, borrower_id
    )
    dossier_repo = SqlAlchemyDossierRepository(pg_session)
    # Старое accountant-досье — должно быть проигнорировано.
    await dossier_repo.save(
        _record(score=10), snapshot_id, "BR-2026-C001", source_mode="accountant",
    )
    # Старое bank-mode досье.
    await dossier_repo.save(
        _record(score=20),
        snapshot_id,
        "BR-2026-C002",
        source_mode="bank",
        created_by_analyst_id=analyst.id,
    )
    # Последнее bank-mode досье — оно должно прийти в ответе.
    latest_id = await dossier_repo.save(
        _record(score=30),
        snapshot_id,
        "BR-2026-C003",
        source_mode="bank",
        created_by_analyst_id=analyst.id,
    )

    headers = await _login(api_client)
    inn = snapshot.borrower.inn.value
    resp = await api_client.get(
        f"/api/bank/borrowers/search?inn={inn}", headers=headers
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert body["dossier_id"] == str(latest_id)
    assert body["score"] == 30
    assert body["display_score"] == 70  # 100 - 30


async def test_search_returns_card_data_when_dossier_exists(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """С досье — populated ``card``: legal_form, recommendation, signals_*,
    business_age_months, monthly_revenue_12m. Источник данных — clean_borrower
    (3 monthly_turnover точки за 2026)."""
    analyst = await _seed_analyst(pg_session)
    snapshot = clean_borrower()
    borrower_id = await SqlAlchemyBorrowerRepository(pg_session).upsert(snapshot.borrower)
    snapshot_id = await SqlAlchemyBorrowerSnapshotRepository(pg_session).save(
        snapshot, borrower_id
    )
    await SqlAlchemyDossierRepository(pg_session).save(
        _record(score=15),  # recommendation="review" в _record
        snapshot_id,
        "BR-2026-C004",
        source_mode="bank",
        created_by_analyst_id=analyst.id,
    )

    headers = await _login(api_client)
    inn = snapshot.borrower.inn.value
    resp = await api_client.get(
        f"/api/bank/borrowers/search?inn={inn}", headers=headers
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["card"] is not None
    card = body["card"]
    assert card["legal_form"] == snapshot.borrower.legal_form.value
    assert card["recommendation"] == "review"
    assert card["signals_total"] == 0  # _record() передаёт red_flags=()
    assert card["signals_evaluated"] == 17
    assert card["business_age_months"] >= 0
    assert isinstance(card["monthly_revenue_12m"], list)
    assert len(card["monthly_revenue_12m"]) == 3  # 3 monthly_turnover точки


async def test_search_card_is_none_when_no_dossier(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Borrower-only ветка — ``card=None`` (нечего рисовать)."""
    await _seed_analyst(pg_session)
    snapshot = clean_borrower()
    await SqlAlchemyBorrowerRepository(pg_session).upsert(snapshot.borrower)

    headers = await _login(api_client)
    resp = await api_client.get(
        f"/api/bank/borrowers/search?inn={snapshot.borrower.inn.value}",
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json()["card"] is None


async def test_search_writes_masked_audit(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session)
    headers = await _login(api_client)

    await api_client.get(
        "/api/bank/borrowers/search?inn=123456789", headers=headers
    )

    rows = (
        await pg_session.execute(
            select(AuditLogORM).where(
                AuditLogORM.event == "search_borrower",
                AuditLogORM.analyst_id == analyst.id,
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].payload["masked_inn"] == "XXXXX6789"
    assert rows[0].payload["result"] == "not_found"


async def test_search_requires_auth(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.get("/api/bank/borrowers/search?inn=999999999")
    assert resp.status_code == 401


async def test_search_rejects_invalid_inn(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)
    headers = await _login(api_client)
    # 10 знаков — недопустимая длина для UZ INN.
    resp = await api_client.get(
        "/api/bank/borrowers/search?inn=1234567890", headers=headers
    )
    assert resp.status_code == 422
