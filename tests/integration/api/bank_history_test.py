"""E2E: GET /api/bank/dossiers — пагинированная история + фильтры."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import replace
from uuid import UUID

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.dossier_record import DossierRecord
from domain.value_objects.inn import INN
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

PASSWORD = "S3cret!"


async def _seed_analyst(session: AsyncSession, email: str) -> AnalystORM:
    hasher = PasswordHasher(rounds=4)
    orm = AnalystORM(
        email=email,
        password_hash=hasher.hash(PASSWORD),
        full_name=f"Аналитик {email}",
        role="analyst",
        is_active=True,
    )
    session.add(orm)
    await session.flush()
    return orm


async def _login(client: httpx.AsyncClient, email: str) -> dict[str, str]:
    resp = await client.post(
        "/api/bank/auth/login", json={"email": email, "password": PASSWORD}
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

    app = create_app()
    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_password_hasher] = _fast_hasher
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


async def _make_bank_dossier(
    session: AsyncSession,
    *,
    analyst_id: UUID,
    inn: str,
    name: str,
    score: int = 25,
    source_mode: str = "bank",
) -> UUID:
    base = clean_borrower()
    borrower = replace(base.borrower, inn=INN(inn), name=name)
    snapshot = replace(base, borrower=borrower)
    borrower_id = await SqlAlchemyBorrowerRepository(session).upsert(borrower)
    snapshot_id = await SqlAlchemyBorrowerSnapshotRepository(session).save(
        snapshot, borrower_id
    )
    record = DossierRecord(
        score=score,
        recommendation="review",
        severity_breakdown={"medium": 1},
        red_flags=(),
        rules_version="v1",
        rules_evaluated=17,
    )
    return await SqlAlchemyDossierRepository(session).save(
        record,
        snapshot_id,
        source_mode=source_mode,
        created_by_analyst_id=analyst_id if source_mode == "bank" else None,
    )


async def test_list_all_bank_dossiers_for_analyst(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session, "a@bank.uz")
    await _make_bank_dossier(
        pg_session, analyst_id=analyst.id, inn="100000001", name='OOO "Alpha"'
    )
    await _make_bank_dossier(
        pg_session, analyst_id=analyst.id, inn="100000002", name='OOO "Beta"'
    )
    headers = await _login(api_client, "a@bank.uz")

    resp = await api_client.get("/api/bank/dossiers", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    inns = {item["borrower_inn_masked"] for item in body["items"]}
    assert inns == {"XXXXX0001", "XXXXX0002"}
    # display_score = 100 - score(25) = 75 для обоих
    assert all(item["display_score"] == 75 for item in body["items"])


async def test_list_filter_mine_excludes_other_analysts(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    a = await _seed_analyst(pg_session, "alpha@bank.uz")
    b = await _seed_analyst(pg_session, "beta@bank.uz")
    await _make_bank_dossier(
        pg_session, analyst_id=a.id, inn="100000010", name='OOO "Alpha"'
    )
    await _make_bank_dossier(
        pg_session, analyst_id=b.id, inn="100000020", name='OOO "Beta"'
    )

    # Аналитик A смотрит "мои" — видит только Alpha.
    headers = await _login(api_client, "alpha@bank.uz")
    resp = await api_client.get("/api/bank/dossiers?filter=mine", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["borrower_name"] == 'OOO "Alpha"'

    # А в режиме "all" — оба досье видны.
    resp_all = await api_client.get("/api/bank/dossiers?filter=all", headers=headers)
    assert resp_all.status_code == 200
    assert resp_all.json()["total"] == 2


async def test_list_excludes_accountant_mode_dossiers(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session, "c@bank.uz")
    await _make_bank_dossier(
        pg_session,
        analyst_id=analyst.id,
        inn="100000030",
        name='OOO "AccOnly"',
        source_mode="accountant",
    )
    await _make_bank_dossier(
        pg_session, analyst_id=analyst.id, inn="100000031", name='OOO "BankOnly"'
    )
    headers = await _login(api_client, "c@bank.uz")

    resp = await api_client.get("/api/bank/dossiers", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["borrower_name"] == 'OOO "BankOnly"'


async def test_list_search_q_matches_inn_or_name(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session, "d@bank.uz")
    await _make_bank_dossier(
        pg_session, analyst_id=analyst.id, inn="100000041", name='OOO "Romashka"'
    )
    await _make_bank_dossier(
        pg_session, analyst_id=analyst.id, inn="100000042", name='OOO "Sirius"'
    )
    headers = await _login(api_client, "d@bank.uz")

    # По имени (case-insensitive substring).
    resp = await api_client.get("/api/bank/dossiers?q=romashka", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    # По ИНН точное совпадение через INN-нормализацию.
    resp_inn = await api_client.get("/api/bank/dossiers?q=100000041", headers=headers)
    assert resp_inn.status_code == 200
    assert resp_inn.json()["total"] == 1


async def test_list_paginated(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session, "e@bank.uz")
    for i in range(5):
        await _make_bank_dossier(
            pg_session,
            analyst_id=analyst.id,
            inn=f"10000005{i}",
            name=f'OOO "N{i}"',
        )
    headers = await _login(api_client, "e@bank.uz")

    page1 = (
        await api_client.get(
            "/api/bank/dossiers?page=1&page_size=2", headers=headers
        )
    ).json()
    page2 = (
        await api_client.get(
            "/api/bank/dossiers?page=2&page_size=2", headers=headers
        )
    ).json()
    page3 = (
        await api_client.get(
            "/api/bank/dossiers?page=3&page_size=2", headers=headers
        )
    ).json()

    assert page1["total"] == 5
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 2
    assert len(page3["items"]) == 1
    # Никаких пересечений между страницами.
    page1_ids = {it["dossier_id"] for it in page1["items"]}
    page2_ids = {it["dossier_id"] for it in page2["items"]}
    assert page1_ids.isdisjoint(page2_ids)


async def test_list_requires_auth(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.get("/api/bank/dossiers")
    assert resp.status_code == 401


async def test_list_response_includes_analyst_name(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session, "f@bank.uz")
    await _make_bank_dossier(
        pg_session, analyst_id=analyst.id, inn="100000060", name='OOO "Z"'
    )
    headers = await _login(api_client, "f@bank.uz")

    resp = await api_client.get("/api/bank/dossiers", headers=headers)
    body = resp.json()
    item = body["items"][0]
    assert item["analyst_id"] == str(analyst.id)
    assert item["analyst_full_name"] == analyst.full_name
