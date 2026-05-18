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

from application.ports.refresh_token_denylist_port import RefreshTokenDenylistPort
from config.settings import Settings
from infrastructure.auth.password_hasher import PasswordHasher
from infrastructure.persistence.database import get_session
from infrastructure.persistence.models.analyst import AnalystORM
from infrastructure.persistence.models.audit_log import AuditLogORM
from interfaces.api.app import create_app
from interfaces.api.bank.dependencies import (
    get_jwt_service,
    get_password_hasher,
    get_refresh_token_denylist,
)
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service

pytestmark = pytest.mark.integration


class _InMemoryRefreshDenylist:
    """T1.2 test double: воспроизводит контракт RefreshTokenDenylistPort
    in-memory. Гарантирует rotation-семантику в bank_auth_test без поднятия
    Redis-контейнера на каждый прогон.
    """

    def __init__(self) -> None:
        self._set: set[str] = set()

    async def deny(self, jti: str, *, expires_at: object) -> bool:
        # expires_at не используется в in-memory fake — Redis adapter clamp'ает
        # TTL, in-memory просто хранит jti до конца теста (rollback).
        _ = expires_at
        if jti in self._set:
            return False
        self._set.add(jti)
        return True

    async def is_denied(self, jti: str) -> bool:
        return jti in self._set

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
    get_refresh_token_denylist.cache_clear()

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield pg_session

    def _fast_hasher() -> PasswordHasher:
        return PasswordHasher(rounds=4)

    # T1.2: in-memory denylist shared между запросами одного теста — даёт
    # rotation-семантику без Redis. Доступен в тесте через
    # ``client.denylist`` для assertions.
    denylist: RefreshTokenDenylistPort = _InMemoryRefreshDenylist()

    def _override_denylist() -> RefreshTokenDenylistPort:
        return denylist

    app = create_app(Settings(app_mode="bank"))
    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_password_hasher] = _fast_hasher
    app.dependency_overrides[get_refresh_token_denylist] = _override_denylist
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            client.denylist = denylist  # type: ignore[attr-defined]
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
    # T1.3 (ADR-0017): email masked в audit_log — partial-identifier остаётся.
    assert log_rows[0].payload.get("email") == "iv***@bank.uz"


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
    body = resp.json()
    assert body["email"] == EMAIL
    # Phase 5 Settings: новые поля для UI Профиль.
    assert "created_at" in body
    assert "password_changed_at" in body
    assert body["mfa_enabled"] is False


async def test_me_returns_mfa_enabled_only_when_enrolled(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Phase 5.B + hotfix `d9387c0` + CA-DS16: mfa_enabled computed-from-
    enrolled_at, не от mfa_secret. /enroll/start пишет secret до verify
    (half-enrolled state) — этот state НЕ должен показывать
    mfa_enabled=True, иначе следующий login потребует TOTP без сохранённого
    secret → lockout. Stored bool удалён в миграции c4f8a1d3e0b2 — enrolled_at
    теперь единственный source of truth.
    """
    from datetime import UTC, datetime

    hasher = PasswordHasher(rounds=4)
    admin_orm = AnalystORM(
        email="admin@bank.uz",
        password_hash=hasher.hash(PASSWORD),
        full_name="Admin A.",
        role="senior_analyst",
        is_active=True,
        # CA-DS16: stored bool удалён. Без enrolled_at → mfa_enabled=False.
    )
    pg_session.add(admin_orm)
    await pg_session.flush()

    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": "admin@bank.uz", "password": PASSWORD}
        )
    ).json()
    me_resp = await api_client.get(
        "/api/bank/auth/me",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert me_resp.status_code == 200
    # Без enrolled_at → False.
    assert me_resp.json()["mfa_enabled"] is False

    # Half-enrolled state: secret записан /enroll/start, verify не прошёл.
    # mfa_enabled всё ещё False (это и есть смысл fix'а).
    admin_orm.mfa_secret = "JBSWY3DPEHPK3PXP"
    await pg_session.flush()
    me_resp2 = await api_client.get(
        "/api/bank/auth/me",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert me_resp2.json()["mfa_enabled"] is False

    # Симулируем успешный /enroll/verify: ставим enrolled_at.
    admin_orm.mfa_enrolled_at = datetime.now(tz=UTC)
    await pg_session.flush()
    me_resp3 = await api_client.get(
        "/api/bank/auth/me",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert me_resp3.json()["mfa_enabled"] is True


async def test_me_returns_401_without_token(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.get("/api/bank/auth/me")
    assert resp.status_code == 401


async def test_me_returns_401_with_garbage_token(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.get(
        "/api/bank/auth/me", headers={"Authorization": "Bearer garbage"}
    )
    assert resp.status_code == 401


async def test_refresh_returns_new_access_and_refresh_pair(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """T1.2: rotation — refresh возвращает обе токена, не только access."""
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
    assert body["refresh_token"]
    assert body["refresh_token"] != refresh
    assert body["token_type"] == "bearer"


async def test_refresh_rotation_invalidates_old_refresh(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """T1.2: после rotation повторный POST со старым refresh → 401 token_reused.

    Закрывает stolen-cookie hole: украденный 7-дневный refresh инвалидируется
    при первой же легитимной rotation owner'а.
    """
    await _seed_analyst(pg_session)
    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    refresh = login["refresh_token"]

    first = await api_client.post(
        "/api/bank/auth/refresh", json={"refresh_token": refresh}
    )
    assert first.status_code == 200

    retry = await api_client.post(
        "/api/bank/auth/refresh", json={"refresh_token": refresh}
    )
    assert retry.status_code == 401
    assert retry.json()["detail"] == "token_reused"


async def test_refresh_double_use_rejected(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """NX-race semantics: после успешного rotation тот же refresh уже в denylist.
    Эквивалентно параллельному запросу с одним и тем же токеном."""
    await _seed_analyst(pg_session)
    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    refresh = login["refresh_token"]

    first = await api_client.post(
        "/api/bank/auth/refresh", json={"refresh_token": refresh}
    )
    assert first.status_code == 200
    second = await api_client.post(
        "/api/bank/auth/refresh", json={"refresh_token": refresh}
    )
    assert second.status_code == 401
    assert second.json()["detail"] == "token_reused"


async def test_refresh_new_token_still_works(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Цепочка rotation: каждый новый refresh действительно валиден."""
    await _seed_analyst(pg_session)
    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    r1 = login["refresh_token"]

    body1 = (
        await api_client.post("/api/bank/auth/refresh", json={"refresh_token": r1})
    ).json()
    r2 = body1["refresh_token"]

    second = await api_client.post(
        "/api/bank/auth/refresh", json={"refresh_token": r2}
    )
    assert second.status_code == 200
    assert second.json()["refresh_token"] != r2


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


async def test_logout_denylists_refresh_token(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """T1.2 (CA-019): logout с refresh_token в body инвалидирует его в denylist —
    последующий /refresh с этим же refresh → 401 token_reused."""
    await _seed_analyst(pg_session)
    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    access = login["access_token"]
    refresh = login["refresh_token"]

    resp = await api_client.post(
        "/api/bank/auth/logout",
        headers={"Authorization": f"Bearer {access}"},
        json={"refresh_token": refresh},
    )
    assert resp.status_code == 204

    retry = await api_client.post(
        "/api/bank/auth/refresh", json={"refresh_token": refresh}
    )
    assert retry.status_code == 401
    assert retry.json()["detail"] == "token_reused"


async def test_logout_without_refresh_token_still_succeeds(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Backward-compat: старые клиенты без refresh_token в body — logout
    audit-only, без denylist. Refresh истечёт натурально через TTL."""
    await _seed_analyst(pg_session)
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


async def test_logout_ignores_cross_account_refresh(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Защита от cross-account abuse: logout не должен denylist'ить чужой
    refresh, даже если злоумышленник передал валидный токен другого user'а.

    Access-токен уже подтвердил identity первого user'а — denylist только
    того refresh'а, чей analyst_id совпадает.
    """
    hasher = PasswordHasher(rounds=4)
    other = AnalystORM(
        email="other@bank.uz",
        password_hash=hasher.hash(PASSWORD),
        full_name="Other O.",
        role="analyst",
        is_active=True,
    )
    pg_session.add(other)
    await pg_session.flush()
    await _seed_analyst(pg_session)

    other_login = (
        await api_client.post(
            "/api/bank/auth/login",
            json={"email": "other@bank.uz", "password": PASSWORD},
        )
    ).json()
    other_refresh = other_login["refresh_token"]

    self_login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    self_access = self_login["access_token"]

    # Logout «нашего» аналитика, но в body — чужой refresh.
    resp = await api_client.post(
        "/api/bank/auth/logout",
        headers={"Authorization": f"Bearer {self_access}"},
        json={"refresh_token": other_refresh},
    )
    assert resp.status_code == 204

    # Чужой refresh всё ещё валиден.
    retry = await api_client.post(
        "/api/bank/auth/refresh", json={"refresh_token": other_refresh}
    )
    assert retry.status_code == 200


# ── change-password (CA-068) ────────────────────────────────────────────────


async def _login_and_get_access(
    api_client: httpx.AsyncClient,
    *,
    email: str = EMAIL,
    password: str = PASSWORD,
) -> str:
    resp = await api_client.post(
        "/api/bank/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    token: str = resp.json()["access_token"]
    return token


async def test_change_password_happy_path_updates_hash_and_timestamp(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """204 → старый пароль 401, новый 200, password_changed_at шагнул вперёд,
    audit пишет ``password_changed``.
    """
    analyst = await _seed_analyst(pg_session)
    initial_changed_at = analyst.password_changed_at
    access = await _login_and_get_access(api_client)

    new_password = "N3wPassw0rd!"
    resp = await api_client.post(
        "/api/bank/auth/change-password",
        headers={"Authorization": f"Bearer {access}"},
        json={"current_password": PASSWORD, "new_password": new_password},
    )
    assert resp.status_code == 204

    # Старый пароль больше не работает.
    old_login = await api_client.post(
        "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert old_login.status_code == 401

    # Новый — работает.
    new_login = await api_client.post(
        "/api/bank/auth/login", json={"email": EMAIL, "password": new_password}
    )
    assert new_login.status_code == 200

    await pg_session.refresh(analyst)
    assert analyst.password_changed_at > initial_changed_at

    log_rows = (
        await pg_session.execute(
            select(AuditLogORM).where(
                AuditLogORM.analyst_id == analyst.id,
                AuditLogORM.event == "password_changed",
            )
        )
    ).scalars().all()
    assert len(log_rows) == 1


async def test_change_password_rejects_invalid_current(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)
    access = await _login_and_get_access(api_client)

    resp = await api_client.post(
        "/api/bank/auth/change-password",
        headers={"Authorization": f"Bearer {access}"},
        json={"current_password": "wrong", "new_password": "N3wPassw0rd!"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid_credentials"


async def test_change_password_rejects_same_as_current(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Compliance-policy: запрет реюза текущего пароля. PASSWORD = "S3cret!"
    короче 12, поэтому Pydantic 422; используем 12+ symbol seed для этой проверки.
    """
    long_password = "OldPassword42!"
    await _seed_analyst(pg_session, password=long_password)
    access = await _login_and_get_access(api_client, password=long_password)

    resp = await api_client.post(
        "/api/bank/auth/change-password",
        headers={"Authorization": f"Bearer {access}"},
        json={"current_password": long_password, "new_password": long_password},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "password_unchanged"


async def test_change_password_rejects_too_short(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)
    access = await _login_and_get_access(api_client)

    resp = await api_client.post(
        "/api/bank/auth/change-password",
        headers={"Authorization": f"Bearer {access}"},
        json={"current_password": PASSWORD, "new_password": "short"},
    )
    assert resp.status_code == 422


async def test_change_password_requires_auth(api_client: httpx.AsyncClient) -> None:
    resp = await api_client.post(
        "/api/bank/auth/change-password",
        json={"current_password": "x", "new_password": "yyyyyyyyyyyy"},
    )
    assert resp.status_code == 401
