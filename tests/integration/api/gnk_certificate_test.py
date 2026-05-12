"""E2E: /api/borrowers/{inn}/gnk-certificate — upload + retrieve + download (T0.3)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings
from infrastructure.auth.password_hasher import PasswordHasher
from infrastructure.persistence.database import get_session
from infrastructure.persistence.models.analyst import AnalystORM
from interfaces.api.app import create_app
from interfaces.api.bank.dependencies import get_jwt_service, get_password_hasher
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service

pytestmark = pytest.mark.integration

EMAIL = "analyst-gnk@bank.uz"
PASSWORD = "S3cret!"


async def _seed_analyst(session: AsyncSession) -> AnalystORM:
    hasher = PasswordHasher(rounds=4)
    orm = AnalystORM(
        email=EMAIL,
        password_hash=hasher.hash(PASSWORD),
        full_name="GNK Analyst",
        role="analyst",
        is_active=True,
    )
    session.add(orm)
    await session.flush()
    return orm


async def _login(client: httpx.AsyncClient) -> str:
    # Backend prefix = /api/bank/auth (bank_auth_router); cookie-обёртку делает
    # Next BFF, на ASGI-уровне токен лежит в JSON body LoginResponse.
    resp = await client.post(
        "/api/bank/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert resp.status_code == 200, resp.text
    return str(resp.json()["access_token"])


@pytest_asyncio.fixture
async def authed_client(pg_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    await _seed_analyst(pg_session)
    get_rule_registry.cache_clear()
    get_scoring_service.cache_clear()
    get_password_hasher.cache_clear()
    get_jwt_service.cache_clear()

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield pg_session

    app = create_app(Settings(app_mode="bank", jwt_secret="x" * 32))
    app.dependency_overrides[get_session] = _override_get_session
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            token = await _login(client)
            # get_current_analyst читает Authorization: Bearer <token>
            # (bank/dependencies.py:98), не cookie — cookie транспортный
            # формат живёт только на Next BFF слое.
            client.headers["Authorization"] = f"Bearer {token}"
            yield client
    finally:
        app.dependency_overrides.clear()


_PDF_HEADER = b"%PDF-1.4\n%EOF"


async def test_upload_returns_201_with_metadata(authed_client: httpx.AsyncClient) -> None:
    resp = await authed_client.post(
        "/api/borrowers/305002665/gnk-certificate",
        data={
            "full_name": '"ZAMIN NOZ NEMATLARI" MCHJ',
            "cert_status": "active",
            "okveds": "47.11, 47.19",
            "cert_id": "GNK-2026-1",
        },
        files={"file": ("cert.pdf", _PDF_HEADER, "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["borrower_inn"] == "305002665"
    assert body["status"] == "active"
    assert body["okveds"] == ["47.11", "47.19"]
    assert body["source"] == "uploaded"
    assert body["file_id"] is not None


async def test_get_latest_returns_uploaded(authed_client: httpx.AsyncClient) -> None:
    await authed_client.post(
        "/api/borrowers/305002665/gnk-certificate",
        data={
            "full_name": "X",
            "cert_status": "active",
            "okveds": "",
        },
        files={"file": ("c.pdf", _PDF_HEADER, "application/pdf")},
    )
    resp = await authed_client.get("/api/borrowers/305002665/gnk-certificate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "X"


async def test_download_returns_binary(authed_client: httpx.AsyncClient) -> None:
    up = await authed_client.post(
        "/api/borrowers/305002665/gnk-certificate",
        data={
            "full_name": "X",
            "cert_status": "active",
            "okveds": "",
        },
        files={"file": ("c.pdf", _PDF_HEADER, "application/pdf")},
    )
    file_id = up.json()["file_id"]
    dl = await authed_client.get(f"/api/gnk-certificates/{file_id}/file")
    assert dl.status_code == 200
    assert dl.content == _PDF_HEADER
    assert dl.headers["content-type"] == "application/pdf"


async def test_upload_rejects_non_pdf_jpg_png(authed_client: httpx.AsyncClient) -> None:
    resp = await authed_client.post(
        "/api/borrowers/305002665/gnk-certificate",
        data={"full_name": "X", "cert_status": "active", "okveds": ""},
        files={"file": ("c.docx", b"binary", "application/vnd.docx")},
    )
    assert resp.status_code == 415


async def test_upload_rejects_invalid_status(authed_client: httpx.AsyncClient) -> None:
    resp = await authed_client.post(
        "/api/borrowers/305002665/gnk-certificate",
        data={"full_name": "X", "cert_status": "freelancer", "okveds": ""},
        files={"file": ("c.pdf", _PDF_HEADER, "application/pdf")},
    )
    assert resp.status_code == 422


async def test_get_latest_404_when_none(authed_client: httpx.AsyncClient) -> None:
    resp = await authed_client.get("/api/borrowers/999999999/gnk-certificate")
    assert resp.status_code == 404


async def test_endpoint_requires_auth_in_bank_mode(
    pg_session: AsyncSession,
) -> None:
    """Bank mode router закрыт auth_required — без cookie → 401."""

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield pg_session

    app = create_app(Settings(app_mode="bank", jwt_secret="x" * 32))
    app.dependency_overrides[get_session] = _override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/borrowers/305002665/gnk-certificate")
    app.dependency_overrides.clear()
    assert resp.status_code == 401
