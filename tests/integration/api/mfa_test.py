"""E2E: /api/bank/auth/mfa/* — full TOTP enrollment/challenge/disable flow."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pyotp
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

EMAIL = "ivanov@bank.uz"
PASSWORD = "S3cret!"


async def _seed_analyst(
    pg_session: AsyncSession,
    *,
    email: str = EMAIL,
    password: str = PASSWORD,
) -> AnalystORM:
    hasher = PasswordHasher(rounds=4)
    orm = AnalystORM(
        email=email,
        password_hash=hasher.hash(password),
        full_name="Иванов И.И.",
        role="analyst",
        is_active=True,
    )
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


async def _login_and_token(api_client: httpx.AsyncClient) -> str:
    resp = await api_client.post(
        "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    return resp.json()["access_token"]


async def test_enroll_start_returns_secret_and_uri(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)
    access = await _login_and_token(api_client)

    resp = await api_client.post(
        "/api/bank/auth/mfa/enroll/start",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["secret"]
    assert body["provisioning_uri"].startswith("otpauth://totp/")


async def test_enroll_verify_with_correct_code_returns_backup_codes(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session)
    access = await _login_and_token(api_client)

    start = (
        await api_client.post(
            "/api/bank/auth/mfa/enroll/start",
            headers={"Authorization": f"Bearer {access}"},
        )
    ).json()
    code = pyotp.TOTP(start["secret"]).now()

    verify = await api_client.post(
        "/api/bank/auth/mfa/enroll/verify",
        json={"code": code},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert verify.status_code == 200
    backups = verify.json()["backup_codes"]
    assert len(backups) == 10
    assert all(len(c) == 8 for c in backups)

    # БД должна иметь enrolled_at + hashed backup codes.
    refreshed = await pg_session.get(AnalystORM, analyst.id)
    assert refreshed is not None
    assert refreshed.mfa_enrolled_at is not None
    assert refreshed.mfa_backup_codes_hash is not None
    assert len(refreshed.mfa_backup_codes_hash) == 10

    # Audit-event mfa_enrolled.
    log_rows = (
        await pg_session.execute(
            select(AuditLogORM).where(
                AuditLogORM.event == "mfa_enrolled",
                AuditLogORM.analyst_id == analyst.id,
            )
        )
    ).scalars().all()
    assert len(log_rows) == 1


async def test_enroll_verify_with_wrong_code_returns_400(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)
    access = await _login_and_token(api_client)
    await api_client.post(
        "/api/bank/auth/mfa/enroll/start",
        headers={"Authorization": f"Bearer {access}"},
    )

    resp = await api_client.post(
        "/api/bank/auth/mfa/enroll/verify",
        json={"code": "000000"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_code"


async def test_login_without_mfa_still_returns_tokens(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    """Backwards compat: existing seeded analysts без MFA — login как раньше."""
    await _seed_analyst(pg_session)
    resp = await api_client.post(
        "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["analyst"]["mfa_enabled"] is False
    # Без MFA — никакого requires_mfa.
    assert "requires_mfa" not in body


async def test_login_with_mfa_returns_challenge_token(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session)
    access = await _login_and_token(api_client)
    start = (
        await api_client.post(
            "/api/bank/auth/mfa/enroll/start",
            headers={"Authorization": f"Bearer {access}"},
        )
    ).json()
    secret = start["secret"]
    code = pyotp.TOTP(secret).now()
    await api_client.post(
        "/api/bank/auth/mfa/enroll/verify",
        json={"code": code},
        headers={"Authorization": f"Bearer {access}"},
    )

    # Теперь login возвращает requires_mfa, не tokens.
    login = await api_client.post(
        "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert login.status_code == 200
    body = login.json()
    assert body.get("requires_mfa") is True
    assert body.get("challenge_token")
    assert "access_token" not in body
    assert analyst.id  # ref used


async def test_mfa_challenge_with_valid_totp_returns_real_tokens(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)
    access = await _login_and_token(api_client)
    start = (
        await api_client.post(
            "/api/bank/auth/mfa/enroll/start",
            headers={"Authorization": f"Bearer {access}"},
        )
    ).json()
    secret = start["secret"]
    code = pyotp.TOTP(secret).now()
    await api_client.post(
        "/api/bank/auth/mfa/enroll/verify",
        json={"code": code},
        headers={"Authorization": f"Bearer {access}"},
    )

    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    chal = await api_client.post(
        "/api/bank/auth/mfa/challenge",
        json={
            "challenge_token": login["challenge_token"],
            "code": pyotp.TOTP(secret).now(),
            "use_backup_code": False,
        },
    )
    assert chal.status_code == 200
    body = chal.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["analyst"]["mfa_enabled"] is True


async def test_mfa_challenge_with_wrong_code_returns_401(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    await _seed_analyst(pg_session)
    access = await _login_and_token(api_client)
    start = (
        await api_client.post(
            "/api/bank/auth/mfa/enroll/start",
            headers={"Authorization": f"Bearer {access}"},
        )
    ).json()
    secret = start["secret"]
    await api_client.post(
        "/api/bank/auth/mfa/enroll/verify",
        json={"code": pyotp.TOTP(secret).now()},
        headers={"Authorization": f"Bearer {access}"},
    )

    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()

    chal = await api_client.post(
        "/api/bank/auth/mfa/challenge",
        json={
            "challenge_token": login["challenge_token"],
            "code": "000000",
            "use_backup_code": False,
        },
    )
    assert chal.status_code == 401
    assert chal.json()["detail"] == "invalid_code"


async def test_mfa_challenge_with_backup_code_consumes_it(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session)
    access = await _login_and_token(api_client)
    start = (
        await api_client.post(
            "/api/bank/auth/mfa/enroll/start",
            headers={"Authorization": f"Bearer {access}"},
        )
    ).json()
    backups = (
        await api_client.post(
            "/api/bank/auth/mfa/enroll/verify",
            json={"code": pyotp.TOTP(start["secret"]).now()},
            headers={"Authorization": f"Bearer {access}"},
        )
    ).json()["backup_codes"]

    login = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()

    # Используем первый backup-code.
    chal = await api_client.post(
        "/api/bank/auth/mfa/challenge",
        json={
            "challenge_token": login["challenge_token"],
            "code": backups[0],
            "use_backup_code": True,
        },
    )
    assert chal.status_code == 200

    # Backup-codes в БД уменьшились до 9.
    refreshed = await pg_session.get(AnalystORM, analyst.id)
    assert refreshed is not None
    assert refreshed.mfa_backup_codes_hash is not None
    assert len(refreshed.mfa_backup_codes_hash) == 9

    # Использованный код больше не работает.
    login2 = (
        await api_client.post(
            "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
    ).json()
    chal2 = await api_client.post(
        "/api/bank/auth/mfa/challenge",
        json={
            "challenge_token": login2["challenge_token"],
            "code": backups[0],
            "use_backup_code": True,
        },
    )
    assert chal2.status_code == 401


async def test_mfa_disable_requires_password_and_code(
    api_client: httpx.AsyncClient, pg_session: AsyncSession
) -> None:
    analyst = await _seed_analyst(pg_session)
    access = await _login_and_token(api_client)
    start = (
        await api_client.post(
            "/api/bank/auth/mfa/enroll/start",
            headers={"Authorization": f"Bearer {access}"},
        )
    ).json()
    secret = start["secret"]
    await api_client.post(
        "/api/bank/auth/mfa/enroll/verify",
        json={"code": pyotp.TOTP(secret).now()},
        headers={"Authorization": f"Bearer {access}"},
    )

    # Wrong password → 401.
    wrong = await api_client.post(
        "/api/bank/auth/mfa/disable",
        json={"password": "wrong", "code": pyotp.TOTP(secret).now()},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert wrong.status_code == 401

    # Right password, wrong code → 401.
    wrong_code = await api_client.post(
        "/api/bank/auth/mfa/disable",
        json={"password": PASSWORD, "code": "000000"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert wrong_code.status_code == 401

    # Both correct → 204, MFA очищена.
    ok = await api_client.post(
        "/api/bank/auth/mfa/disable",
        json={"password": PASSWORD, "code": pyotp.TOTP(secret).now()},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert ok.status_code == 204

    refreshed = await pg_session.get(AnalystORM, analyst.id)
    assert refreshed is not None
    assert refreshed.mfa_secret is None
    assert refreshed.mfa_enrolled_at is None
    assert refreshed.mfa_backup_codes_hash is None
