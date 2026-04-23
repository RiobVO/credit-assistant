"""Integration: POST /api/manual-input/parse-files.

Multipart-загрузка FORM_2 + VAT_DECLARATION → ParsedFinancialsResponse.
Endpoint stateless (БД не использует), поэтому только ASGITransport, без
testcontainer.

Mode-gating проверяется отдельно: в bank — 401 без токена; в accountant —
открыт. Здесь — accountant default.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from io import BytesIO

import httpx
import pytest
import pytest_asyncio

from interfaces.api.app import create_app
from tests.fixtures.soliq_xltx._factories import (
    build_form2_income_statement_wb,
    build_vat_declaration_wb,
)

pytestmark = pytest.mark.integration

ENDPOINT = "/api/manual-input/parse-files"


def _bytes(wb: object) -> bytes:
    buf = BytesIO()
    wb.save(buf)  # type: ignore[attr-defined]
    buf.seek(0)
    return buf.read()


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    """Stateless endpoint — БД не нужна. Дефолтный APP_MODE из settings."""
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_parse_form2_returns_annual_revenue_and_net_profit(
    api_client: httpx.AsyncClient,
) -> None:
    """Real-shape FORM_2 Q4 2025 → revenue_by_year + net_profit_by_year заполняются."""
    form2_bytes = _bytes(
        build_form2_income_statement_wb(
            period_year=2025,
            period_quarter=4,
            revenue_current=5973686.0,
            revenue_prior=6559649.0,
        )
    )

    response = await api_client.post(
        ENDPOINT,
        files=[("files", ("form2.xltx", form2_bytes, "application/octet-stream"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["revenue_by_year"]["2025"] == "5973686000"
    assert body["revenue_by_year"]["2024"] == "6559649000"
    assert "FORM_2 Q4 2025" in body["source_trail"]["revenue_2025"]
    assert body["parse_warnings"] == []


@pytest.mark.asyncio
async def test_parse_mixed_form2_and_vat(api_client: httpx.AsyncClient) -> None:
    form2 = _bytes(build_form2_income_statement_wb(period_year=2025, period_quarter=4))
    vat = _bytes(build_vat_declaration_wb(period_year=2026))

    response = await api_client.post(
        ENDPOINT,
        files=[
            ("files", ("form2.xltx", form2, "application/octet-stream")),
            ("files", ("vat.xltx", vat, "application/octet-stream")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert "2025" in body["revenue_by_year"]
    assert "2026" in body["vat_declared_by_year"]


@pytest.mark.asyncio
async def test_unsupported_file_yields_warning_200(api_client: httpx.AsyncClient) -> None:
    """Битый бинарник не валит запрос — warning + 200."""
    response = await api_client.post(
        ENDPOINT,
        files=[("files", ("trash.bin", b"\x00garbage", "application/octet-stream"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["revenue_by_year"] == {}
    assert any("trash.bin" in w for w in body["parse_warnings"])


@pytest.mark.asyncio
async def test_empty_file_list_422(api_client: httpx.AsyncClient) -> None:
    """Multipart без файлов → 422 (FastAPI validation)."""
    response = await api_client.post(ENDPOINT)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_too_many_files_422(api_client: httpx.AsyncClient) -> None:
    """Лимит 10 файлов за запрос → 422 при 11."""
    form2 = _bytes(build_form2_income_statement_wb())
    files = [
        ("files", (f"form2_{i}.xltx", form2, "application/octet-stream"))
        for i in range(11)
    ]

    response = await api_client.post(ENDPOINT, files=files)

    assert response.status_code == 422
    assert "лимит" in response.json()["detail"].lower()
