"""E2E: /api/bank/admin/* против real Postgres (CA-DS13).

Сценарии reset-mfa: happy 204 + mfa fields очищены + audit пишет
mfa_admin_reset с target в payload; 403 для не-senior_analyst; 404 на
несуществующего email; 401 без Bearer.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

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
from interfaces.api.app import create_app
from interfaces.api.bank.dependencies import get_jwt_service, get_password_hasher
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service

pytestmark = pytest.mark.integration

SENIOR_EMAIL = "senior@bank.uz"
TARGET_EMAIL = "ivanov@bank.uz"
PASSWORD = "Sup3rSecret!"


async def _seed_analyst(
    pg_session: AsyncSession,
    *,
    email: str,
    role: str = "analyst",
    with_mfa: bool = False,
) -> AnalystORM:
    hasher = PasswordHasher(rounds=4)
    orm = AnalystORM(
        email=email,
        password_hash=hasher.hash(PASSWORD),
        full_name=email,
        role=role,
        is_active=True,
    )
    if with_mfa:
        orm.mfa_secret = "JBSWY3DPEHPK3PXP"
        orm.mfa_enrolled_at = datetime.now(tz=UTC)
        orm.mfa_backup_codes_hash = ["$2b$04$dummy.hash.for.test"]
        orm.mfa_enabled = True
    pg_session.add(orm)
    await pg_session.flush()
    return orm


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


async def _login(api_client: httpx.AsyncClient, email: str) -> str:
    resp = await api_client.post(
        "/api/bank/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert resp.status_code == 200, resp.text
    token: str = resp.json()["access_token"]
    return token


async def test_reset_mfa_happy_path_clears_fields_and_writes_audit(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    senior = await _seed_analyst(pg_session, email=SENIOR_EMAIL, role="senior_analyst")
    target = await _seed_analyst(pg_session, email=TARGET_EMAIL, with_mfa=True)
    senior_access = await _login(api_client, SENIOR_EMAIL)

    resp = await api_client.post(
        "/api/bank/admin/analysts/reset-mfa",
        headers={"Authorization": f"Bearer {senior_access}"},
        json={"email": TARGET_EMAIL},
    )
    assert resp.status_code == 204

    await pg_session.refresh(target)
    assert target.mfa_secret is None
    assert target.mfa_enrolled_at is None
    assert target.mfa_backup_codes_hash is None
    assert target.mfa_enabled is False

    rows = (
        await pg_session.execute(
            select(AuditLogORM).where(
                AuditLogORM.analyst_id == senior.id,
                AuditLogORM.event == "mfa_admin_reset",
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    payload = rows[0].payload
    assert payload["target_email"] == TARGET_EMAIL
    assert payload["target_analyst_id"] == str(target.id)


async def test_reset_mfa_forbidden_for_regular_analyst(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session, email=SENIOR_EMAIL, role="analyst")
    await _seed_analyst(pg_session, email=TARGET_EMAIL, with_mfa=True)
    access = await _login(api_client, SENIOR_EMAIL)

    resp = await api_client.post(
        "/api/bank/admin/analysts/reset-mfa",
        headers={"Authorization": f"Bearer {access}"},
        json={"email": TARGET_EMAIL},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "forbidden"


async def test_reset_mfa_not_found_when_email_unknown(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session, email=SENIOR_EMAIL, role="senior_analyst")
    access = await _login(api_client, SENIOR_EMAIL)

    resp = await api_client.post(
        "/api/bank/admin/analysts/reset-mfa",
        headers={"Authorization": f"Bearer {access}"},
        json={"email": "ghost@bank.uz"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "analyst_not_found"


async def test_reset_mfa_requires_auth(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.post(
        "/api/bank/admin/analysts/reset-mfa",
        json={"email": TARGET_EMAIL},
    )
    assert resp.status_code == 401
