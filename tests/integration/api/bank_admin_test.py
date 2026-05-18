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
        # CA-DS16: stored bool удалён, enrolled_at — single source.
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
    # CA-DS16: enrolled_at IS NULL ⇔ computed mfa_enabled=False.

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
    # T1.3 (ADR-0017): target_email masked в audit.
    assert payload["target_email"] == "iv***@bank.uz"
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


# T3.5 — audit-log CSV export.


async def _seed_audit_row(
    pg_session: AsyncSession,
    *,
    analyst_id: object,
    event: str,
    created_at: datetime,
    payload: dict[str, object] | None = None,
    request_id: str | None = None,
) -> None:
    row = AuditLogORM(
        analyst_id=analyst_id,
        event=event,
        payload=payload or {},
        request_id=request_id,
        brand_id="default",
    )
    pg_session.add(row)
    await pg_session.flush()
    # Override server_default created_at напрямую (после flush — есть id).
    row.created_at = created_at
    await pg_session.flush()


async def test_audit_export_happy_path_returns_csv(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    senior = await _seed_analyst(pg_session, email=SENIOR_EMAIL, role="senior_analyst")
    await _seed_audit_row(
        pg_session,
        analyst_id=senior.id,
        event="login",
        created_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
        request_id="abc12345" + "0" * 24,
    )
    await _seed_audit_row(
        pg_session,
        analyst_id=senior.id,
        event="view_dossier",
        created_at=datetime(2026, 5, 17, 11, 0, tzinfo=UTC),
        payload={"masked_inn": "XXXXXX1234"},
    )

    access = await _login(api_client, SENIOR_EMAIL)
    resp = await api_client.get(
        "/api/bank/admin/audit-log/export",
        headers={"Authorization": f"Bearer {access}"},
        params={"from": "2026-05-17T00:00:00Z", "to": "2026-05-18T00:00:00Z"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    assert "audit-log-20260517-20260518.csv" in resp.headers["content-disposition"]

    csv_text = resp.text
    lines = csv_text.strip().splitlines()
    # header + 2 seeded rows + audit_log_export сам себе (записывается до stream)
    assert lines[0].startswith("id,created_at,brand_id,request_id,event,")
    events = [line.split(",")[4] for line in lines[1:]]
    # хронологический порядок: login → view_dossier; audit_log_export может
    # попасть либо в выборку (created_at NOW попадает в окно если to в будущем),
    # либо нет — но 2 наших точно присутствуют.
    assert "login" in events
    assert "view_dossier" in events


async def test_audit_export_event_filter(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    senior = await _seed_analyst(pg_session, email=SENIOR_EMAIL, role="senior_analyst")
    await _seed_audit_row(
        pg_session,
        analyst_id=senior.id,
        event="login",
        created_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
    )
    await _seed_audit_row(
        pg_session,
        analyst_id=senior.id,
        event="view_dossier",
        created_at=datetime(2026, 5, 17, 11, 0, tzinfo=UTC),
    )

    access = await _login(api_client, SENIOR_EMAIL)
    resp = await api_client.get(
        "/api/bank/admin/audit-log/export",
        headers={"Authorization": f"Bearer {access}"},
        params={
            "from": "2026-05-17T00:00:00Z",
            "to": "2026-05-18T00:00:00Z",
            "event": "login",
        },
    )
    assert resp.status_code == 200
    events = [line.split(",")[4] for line in resp.text.strip().splitlines()[1:]]
    assert "login" in events
    assert "view_dossier" not in events


async def test_audit_export_forbidden_for_regular_analyst(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session, email=SENIOR_EMAIL, role="analyst")
    access = await _login(api_client, SENIOR_EMAIL)
    resp = await api_client.get(
        "/api/bank/admin/audit-log/export",
        headers={"Authorization": f"Bearer {access}"},
        params={"from": "2026-05-17T00:00:00Z", "to": "2026-05-18T00:00:00Z"},
    )
    assert resp.status_code == 403


async def test_audit_export_invalid_date_range(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session, email=SENIOR_EMAIL, role="senior_analyst")
    access = await _login(api_client, SENIOR_EMAIL)
    resp = await api_client.get(
        "/api/bank/admin/audit-log/export",
        headers={"Authorization": f"Bearer {access}"},
        params={"from": "2026-05-18T00:00:00Z", "to": "2026-05-17T00:00:00Z"},
    )
    assert resp.status_code == 422


async def test_audit_export_self_logs_to_audit(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Сам факт экспорта пишется в audit_log."""
    senior = await _seed_analyst(pg_session, email=SENIOR_EMAIL, role="senior_analyst")
    access = await _login(api_client, SENIOR_EMAIL)
    resp = await api_client.get(
        "/api/bank/admin/audit-log/export",
        headers={"Authorization": f"Bearer {access}"},
        params={"from": "2026-05-17T00:00:00Z", "to": "2026-05-18T00:00:00Z"},
    )
    assert resp.status_code == 200

    rows = (
        await pg_session.execute(
            select(AuditLogORM).where(
                AuditLogORM.analyst_id == senior.id,
                AuditLogORM.event == "audit_log_export",
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    payload = rows[0].payload
    assert payload["from"].startswith("2026-05-17")
    assert payload["to"].startswith("2026-05-18")
    assert "rows_count" in payload
