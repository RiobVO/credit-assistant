"""E2E: GET /api/dossier/{id}/pdf против real Postgres + WeasyPrint.

Сценарий: создаём досье через POST /api/manual-input, скачиваем PDF через
GET /api/dossier/{id}/pdf, проверяем magic bytes и Content-Disposition.

WeasyPrint требует Pango/HarfBuzz нативно — на Windows-хосте без GTK
endpoint вернёт 503. Эти тесты идут в общем integration-наборе (Docker
с testcontainers), где Pango есть.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.database import get_session
from interfaces.api.app import create_app
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        sys.platform == "win32",
        reason="WeasyPrint требует GTK runtime — запускайте в Docker (credit-api)",
    ),
]

POST_ENDPOINT = "/api/manual-input"
PDF_ENDPOINT_TEMPLATE = "/api/dossier/{dossier_id}/pdf"
BORROWER_INN = "100000999"

PDF_MAGIC = b"%PDF-"


@pytest_asyncio.fixture
async def api_client(pg_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    get_rule_registry.cache_clear()
    get_scoring_service.cache_clear()

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
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


def _payload() -> dict[str, Any]:
    monthly = [
        {"month_start": f"2025-{m:02d}-01", "revenue": _money("1000000000")}
        for m in range(1, 13)
    ]
    return {
        "borrower": {
            "inn": BORROWER_INN,
            "name": "ООО «PDF E2E»",
            "legal_form": "llc",
            "registration_date": "2019-03-15",
            "director_name": "Каримов Ш.А.",
            "director_appointed_at": "2021-06-01",
            "okved_main": "46.49",
            "registered_address": "Ташкент",
        },
        "as_of": "2026-05-08",
        "monthly_turnover": monthly,
    }


async def test_pdf_endpoint_returns_pdf_bytes_with_attachment_header(
    api_client: httpx.AsyncClient,
) -> None:
    create = await api_client.post(POST_ENDPOINT, json=_payload())
    assert create.status_code == 200, create.text
    dossier_id = create.json()["dossier_id"]

    r = await api_client.get(PDF_ENDPOINT_TEMPLATE.format(dossier_id=dossier_id))

    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"

    disposition = r.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert "BR-" in disposition
    assert ".pdf" in disposition

    assert r.content.startswith(PDF_MAGIC), f"первые 8 байт: {r.content[:8]!r}"
    assert len(r.content) > 5000, f"PDF слишком маленький: {len(r.content)} bytes"


async def test_pdf_endpoint_returns_404_for_unknown_id(
    api_client: httpx.AsyncClient,
) -> None:
    unknown = UUID("00000000-0000-0000-0000-000000000000")
    r = await api_client.get(PDF_ENDPOINT_TEMPLATE.format(dossier_id=str(unknown)))

    assert r.status_code == 404
    assert r.json()["detail"] == "Досье не найдено"


async def test_pdf_endpoint_returns_422_for_malformed_uuid(
    api_client: httpx.AsyncClient,
) -> None:
    r = await api_client.get("/api/dossier/not-a-uuid/pdf")
    assert r.status_code == 422
