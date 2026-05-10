"""E2E: /api/bank/auth/* против real Postgres.

Сценарии: успешный login, неверный пароль, неактивный аналитик, refresh
со свежим/невалидным/access-токеном, /me с токеном/без, logout.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.auth.password_hasher import PasswordHasher
from infrastructure.persistence.database import get_session
from infrastructure.persistence.models.analyst import AnalystORM
from infrastructure.persistence.models.audit_log import AuditLogORM
from interfaces.api.app import create_app
from interfaces.api.bank.dependencies import get_jwt_service, get_password_hasher
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service

pytestmark = pytest.mark.integration

EMAIL = "ivanov@bank.uz"
PASSWORD = "S3cret!"


async def _seed_analyst(
    pg_session: AsyncSession,
    *,
    email: str = EMAIL,
    password: str = PASSWORD,
    is_active: bool = True,
) -> AnalystORM:
    hasher = PasswordHasher(rounds=4)
    orm = AnalystORM(
        email=email,
        password_hash=hasher.hash(password),
        full_name="Иванов И.И.",
        role="analyst",
        is_active=is_active,
    )
    pg_session.add(orm)
    await pg_session.flush()
    return orm


@pytest_asyncio.fixture
async def api_client(pg_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    get_rule_registry.cache_clear()
    get_scoring_service.cache_clear()
    get_jwt_service.cache_clear()
    # Hasher с cost=4 для unit-уровня скорости тестов.
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


async def test_login_success_returns_tokens_and_writes_audit(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session)

    resp = await api_client.post(
        "/api/bank/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["analyst"]["email"] == EMAIL
    assert body["analyst"]["id"] == str(analyst.id)

    log_rows = (
        await pg_session.execute(
            select(AuditLogORM).where(AuditLogORM.analyst_id == analyst.id)
        )
    ).scalars().all()
    assert [r.event for r in log_rows] == ["login"]


async def test_login_invalid_password_returns_401_and_writes_failed_audit(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)

    resp = await api_client.post(
        "/api/bank/auth/login",
        json={"email": EMAIL, "password": "wrong"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid_credentials"

    log_rows = (
        await pg_session.execute(
            select(AuditLogORM).where(AuditLogORM.event == "login_failed")
        )
    ).scalars().all()
    assert len(log_rows) == 1
    assert log_rows[0].payload.get("email") == EMAIL


async def test_login_unknown_email_returns_401(
    api_client: httpx.AsyncClient,
) -> None:
    resp = await api_client.post(
        "/api/bank/auth/login",
        json={"email": "nobody@bank.uz", "password": "anything"},
    )
    assert resp.status_code == 401


async def test_login_inactive_analyst_returns_401(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session, is_active=False)
    resp = await api_client.post(
        "/api/bank/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
    )
    assert resp.status_code == 401


async def test_me_returns_analyst_with_valid_access_token(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)
    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    access = login["access_token"]

    resp = await api_client.get(
        "/api/bank/auth/me", headers={"Authorization": f"Bearer {access}"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == EMAIL


async def test_me_returns_401_without_token(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.get("/api/bank/auth/me")
    assert resp.status_code == 401


async def test_me_returns_401_with_garbage_token(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.get(
        "/api/bank/auth/me", headers={"Authorization": "Bearer garbage"}
    )
    assert resp.status_code == 401


async def test_refresh_returns_new_access_token(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)
    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    refresh = login["refresh_token"]

    resp = await api_client.post(
        "/api/bank/auth/refresh", json={"refresh_token": refresh}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


async def test_refresh_rejects_access_token(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Access на refresh-endpoint должен отвергаться — typ check."""
    await _seed_analyst(pg_session)
    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    access = login["access_token"]

    resp = await api_client.post(
        "/api/bank/auth/refresh", json={"refresh_token": access}
    )
    assert resp.status_code == 401


async def test_refresh_rejects_inactive_analyst(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Refresh должен проверить is_active в БД, а не доверять токену слепо."""
    analyst = await _seed_analyst(pg_session)
    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    refresh = login["refresh_token"]

    analyst.is_active = False
    await pg_session.flush()

    resp = await api_client.post(
        "/api/bank/auth/refresh", json={"refresh_token": refresh}
    )
    assert resp.status_code == 401


async def test_logout_writes_audit_and_returns_204(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session)
    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    access = login["access_token"]

    resp = await api_client.post(
        "/api/bank/auth/logout",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 204

    log_rows = (
        await pg_session.execute(
            select(AuditLogORM).where(
                AuditLogORM.analyst_id == analyst.id,
                AuditLogORM.event == "logout",
            )
        )
    ).scalars().all()
    assert len(log_rows) == 1


async def test_logout_requires_auth(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.post("/api/bank/auth/logout")
    assert resp.status_code == 401
