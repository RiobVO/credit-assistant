"""E2E: POST /api/manual-input + draft endpoints против real Postgres.

Override get_session возвращает pg_session (с outer-tx и savepoint).
Endpoint вызывает свой `session.begin()` — благодаря join_transaction_mode
он создаёт savepoint, коммит savepoint'а внутри outer-tx безопасен.
По окончанию теста outer-tx откатывается, БД возвращается в исходное.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.database import get_session
from infrastructure.persistence.models.borrower import BorrowerORM
from infrastructure.persistence.models.borrower_snapshot import BorrowerSnapshotORM
from infrastructure.persistence.models.dossier import DossierORM
from infrastructure.persistence.models.draft import DraftORM
from interfaces.api.app import create_app
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service

pytestmark = pytest.mark.integration

ENDPOINT = "/api/manual-input"
DRAFT_ENDPOINT = "/api/manual-input/draft"
BORROWER_INN = "100000777"


@pytest_asyncio.fixture
async def api_client(pg_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    """FastAPI app с подменённым get_session на pg_session."""
    get_rule_registry.cache_clear()
    get_scoring_service.cache_clear()

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        # Endpoint оборачивает session в свой `session.begin()` — у нас уже
        # активная outer transaction, поэтому begin создаст savepoint
        # (join_transaction_mode="create_savepoint" в pg_session фикстуре).
        yield pg_session

    app = create_app()
    app.dependency_overrides[get_session] = _override_get_session
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _money(amount: str) -> dict[str, str]:
    return {"amount": amount, "currency": "UZS"}


def _borrower() -> dict[str, Any]:
    return {
        "inn": BORROWER_INN,
        "name": 'OOO "E2E Test"',
        "legal_form": "llc",
        "registration_date": "2018-05-01",
        "director_name": "Director D.D.",
        "director_appointed_at": "2020-01-01",
        "okved_main": "46.49",
        "registered_address": "Tashkent, ul. 1",
        "okved_main_changed_at": None,
    }


async def test_manual_input_persists_full_dossier_chain(
    api_client: httpx.AsyncClient,
    pg_session: AsyncSession,
) -> None:
    payload = {
        "borrower": _borrower(),
        "as_of": "2026-05-08",
    }
    r = await api_client.post(ENDPOINT, json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    dossier_id = UUID(body["dossier_id"])

    # В одной outer-transaction видим записи, которые endpoint commit'нул в свой savepoint.
    borrower_rows = (
        await pg_session.execute(
            select(BorrowerORM).where(BorrowerORM.inn == BORROWER_INN)
        )
    ).scalars().all()
    assert len(borrower_rows) == 1
    assert borrower_rows[0].name == 'OOO "E2E Test"'

    snapshot_rows = (
        await pg_session.execute(
            select(BorrowerSnapshotORM).where(
                BorrowerSnapshotORM.borrower_id == borrower_rows[0].id
            )
        )
    ).scalars().all()
    assert len(snapshot_rows) == 1

    dossier_orm = await pg_session.get(DossierORM, dossier_id)
    assert dossier_orm is not None
    assert dossier_orm.snapshot_id == snapshot_rows[0].id
    assert dossier_orm.rules_evaluated == 24  # ADR-0024 Session 2: +OFF_BALANCE/CASH_FLOW


async def test_draft_create_get_update_404_cycle(
    api_client: httpx.AsyncClient,
    pg_session: AsyncSession,
) -> None:
    # Create.
    r = await api_client.post(DRAFT_ENDPOINT, json={"payload": {"step1": {"inn": "1"}}})
    assert r.status_code == 201, r.text
    draft_id = r.json()["draft_id"]
    assert "expires_at" in r.json()

    # Get.
    r = await api_client.get(f"{DRAFT_ENDPOINT}/{draft_id}")
    assert r.status_code == 200
    assert r.json()["payload"] == {"step1": {"inn": "1"}}

    # Update.
    r = await api_client.put(
        f"{DRAFT_ENDPOINT}/{draft_id}",
        json={"payload": {"step1": {"inn": "2"}}},
    )
    assert r.status_code == 200

    # Get after update.
    r = await api_client.get(f"{DRAFT_ENDPOINT}/{draft_id}")
    assert r.status_code == 200
    assert r.json()["payload"] == {"step1": {"inn": "2"}}

    # Update unknown — 404.
    r = await api_client.put(
        f"{DRAFT_ENDPOINT}/00000000-0000-0000-0000-000000000000",
        json={"payload": {"k": "v"}},
    )
    assert r.status_code == 404

    # Get unknown — 404.
    r = await api_client.get(f"{DRAFT_ENDPOINT}/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404

    # В БД ровно 1 строка после всего цикла.
    rows = (await pg_session.execute(select(DraftORM))).scalars().all()
    assert len(rows) == 1
    assert str(rows[0].id) == draft_id
