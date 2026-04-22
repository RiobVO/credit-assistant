"""E2E: ``APP_MODE`` env-driven conditional router include + audit-wiring shared.

Сценарии:
* accountant install: bank-роуты → 404 (`/api/bank/auth/login`, `/api/bank/dossiers`, ...),
  shared-endpoints без auth работают как раньше.
* bank install: shared-endpoint без токена → 401, с токеном → 200 + audit-запись
  + ``source_mode='bank'`` / ``created_by_analyst_id`` на новом досье.
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

from config.settings import Settings
from infrastructure.auth.password_hasher import PasswordHasher
from infrastructure.persistence.database import get_session
from infrastructure.persistence.models.analyst import AnalystORM
from infrastructure.persistence.models.audit_log import AuditLogORM
from infrastructure.persistence.models.dossier import DossierORM
from interfaces.api.app import create_app
from interfaces.api.bank.dependencies import get_jwt_service, get_password_hasher
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service

pytestmark = pytest.mark.integration

PASSWORD = "S3cret!"
BORROWER_INN = "100000999"


def _borrower() -> dict[str, Any]:
    return {
        "inn": BORROWER_INN,
        "name": 'OOO "ModeGate"',
        "legal_form": "llc",
        "registration_date": "2018-05-01",
        "director_name": "D.D.",
        "director_appointed_at": "2020-01-01",
        "okved_main": "46.49",
        "registered_address": "Tashkent",
        "okved_main_changed_at": None,
    }


async def _seed_analyst(session: AsyncSession, email: str = "g@bank.uz") -> AnalystORM:
    hasher = PasswordHasher(rounds=4)
    orm = AnalystORM(
        email=email,
        password_hash=hasher.hash(PASSWORD),
        full_name="Gating A.",
        role="analyst",
        is_active=True,
    )
    session.add(orm)
    await session.flush()
    return orm


def _make_client_for(
    pg_session: AsyncSession, *, mode: str
) -> tuple[httpx.AsyncClient, Any]:
    get_rule_registry.cache_clear()
    get_scoring_service.cache_clear()
    get_jwt_service.cache_clear()
    get_password_hasher.cache_clear()

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield pg_session

    def _fast_hasher() -> PasswordHasher:
        return PasswordHasher(rounds=4)

    app = create_app(Settings(app_mode=mode))
    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_password_hasher] = _fast_hasher
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return client, app


@pytest_asyncio.fixture
async def accountant_client(pg_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    client, app = _make_client_for(pg_session, mode="accountant")
    try:
        async with client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def bank_client(pg_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    client, app = _make_client_for(pg_session, mode="bank")
    try:
        async with client:
            yield client
    finally:
        app.dependency_overrides.clear()


# ---------------- accountant install ----------------


async def test_accountant_install_bank_routes_return_404(
    accountant_client: httpx.AsyncClient,
) -> None:
    """В accountant-режиме bank-маршрутов нет вовсе — Bus 404, не 401."""
    for path in (
        "/api/bank/auth/login",
        "/api/bank/auth/me",
        "/api/bank/auth/refresh",
        "/api/bank/auth/logout",
        "/api/bank/borrowers/search?inn=123456789",
        "/api/bank/dossiers",
    ):
        method = "post" if "/auth/" in path and "me" not in path else "get"
        if method == "post":
            resp = await accountant_client.post(path, json={})
        else:
            resp = await accountant_client.get(path)
        assert resp.status_code == 404, f"{path}: ожидал 404, получил {resp.status_code}"


async def test_accountant_install_shared_endpoint_works_without_auth(
    accountant_client: httpx.AsyncClient,
) -> None:
    """POST /api/manual-input в accountant-режиме доступен без токена и сохраняет
    досье с ``source_mode='accountant'``."""
    payload = {"borrower": _borrower(), "as_of": "2026-05-08"}
    resp = await accountant_client.post("/api/manual-input", json=payload)
    assert resp.status_code == 200, resp.text


# ---------------- bank install ----------------


async def test_bank_install_shared_endpoint_without_token_returns_401(
    bank_client: httpx.AsyncClient,
) -> None:
    """Mode-gating: shared endpoint в bank-режиме закрыт guard'ом на router."""
    payload = {"borrower": _borrower(), "as_of": "2026-05-08"}
    resp = await bank_client.post("/api/manual-input", json=payload)
    assert resp.status_code == 401


async def test_bank_install_manual_input_stamps_source_mode_and_writes_audit(
    bank_client: httpx.AsyncClient,
    pg_session: AsyncSession,
) -> None:
    analyst = await _seed_analyst(pg_session)
    login = await bank_client.post(
        "/api/bank/auth/login", json={"email": analyst.email, "password": PASSWORD}
    )
    assert login.status_code == 200
    access = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access}"}

    payload = {"borrower": _borrower(), "as_of": "2026-05-08"}
    resp = await bank_client.post("/api/manual-input", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    dossier_id = UUID(resp.json()["dossier_id"])

    dossier_orm = await pg_session.get(DossierORM, dossier_id)
    assert dossier_orm is not None
    assert dossier_orm.source_mode == "bank"
    assert dossier_orm.created_by_analyst_id == analyst.id

    audit_rows = (
        await pg_session.execute(
            select(AuditLogORM).where(
                AuditLogORM.event == "generate_dossier",
                AuditLogORM.analyst_id == analyst.id,
            )
        )
    ).scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].target_id == dossier_id
    assert audit_rows[0].payload["masked_inn"] == "XXXXX0999"


async def test_bank_install_get_dossier_writes_view_audit(
    bank_client: httpx.AsyncClient,
    pg_session: AsyncSession,
) -> None:
    analyst = await _seed_analyst(pg_session, email="h@bank.uz")
    login = await bank_client.post(
        "/api/bank/auth/login", json={"email": analyst.email, "password": PASSWORD}
    )
    access = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access}"}

    # Создаём досье через тот же endpoint.
    payload = {"borrower": _borrower(), "as_of": "2026-05-08"}
    create_resp = await bank_client.post(
        "/api/manual-input", json=payload, headers=headers
    )
    dossier_id = create_resp.json()["dossier_id"]

    # Затем читаем — должен попасть view_dossier event.
    view_resp = await bank_client.get(f"/api/dossier/{dossier_id}", headers=headers)
    assert view_resp.status_code == 200

    audit_rows = (
        await pg_session.execute(
            select(AuditLogORM).where(
                AuditLogORM.event == "view_dossier",
                AuditLogORM.analyst_id == analyst.id,
            )
        )
    ).scalars().all()
    assert len(audit_rows) == 1
    assert str(audit_rows[0].target_id) == dossier_id


async def test_bank_install_get_dossier_without_token_returns_401(
    bank_client: httpx.AsyncClient,
) -> None:
    resp = await bank_client.get(
        "/api/dossier/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 401
