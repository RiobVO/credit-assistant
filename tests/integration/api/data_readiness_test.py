"""Integration: POST /api/manual-input/readiness.

Stateless endpoint (БД не использует) — только ASGITransport, без
testcontainer. Frontend дебаунсит запросы; здесь мы проверяем
семантику ответа по 4 уровням + edge cases.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio

from interfaces.api.app import create_app

pytestmark = pytest.mark.integration

ENDPOINT = "/api/manual-input/readiness"


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_empty_payload_yields_insufficient(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(ENDPOINT, json={})
    assert response.status_code == 200
    body = response.json()
    assert body["level"] == "insufficient"
    assert body["years_covered"] == []
    assert body["full_years"] == []
    assert body["confidence_score"] == "0"
    assert set(body["missing_capabilities"]) == {
        "yoy_trend",
        "cagr",
        "balance_ratios",
        "tax_burden",
    }


@pytest.mark.asyncio
async def test_one_annual_year_yields_minimal(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(
        ENDPOINT,
        json={"annual_report_years": [2025], "source_trail": {"revenue_2025": "FORM_2"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["level"] == "minimal"
    assert body["full_years"] == [2025]
    assert body["parser_sources"] == ["form_2"]
    assert body["confidence_score"] == "0.25"


@pytest.mark.asyncio
async def test_two_consecutive_years_yield_standard(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.post(
        ENDPOINT,
        json={
            "annual_report_years": [2024, 2025],
            "source_trail": {"revenue_2024": "FORM_2", "revenue_2025": "FORM_2"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["level"] == "standard"
    assert body["years_covered"] == [2024, 2025]
    assert "cagr" in body["missing_capabilities"]
    assert "yoy_trend" not in body["missing_capabilities"]


@pytest.mark.asyncio
async def test_three_years_form1_and_esf_yield_comprehensive(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.post(
        ENDPOINT,
        json={
            "annual_report_years": [2023, 2024, 2025],
            "source_trail": {
                "revenue_2025": "FORM_2",
                "form1.assets_total": "FORM_1",
                "esf_2025_q4": "ESF",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["level"] == "comprehensive"
    assert body["missing_capabilities"] == []
    assert set(body["parser_sources"]) == {"form_1", "form_2", "esf_csv"}
    assert body["confidence_score"] == "1"


@pytest.mark.asyncio
async def test_unknown_source_trail_keys_silently_ignored(
    api_client: httpx.AsyncClient,
) -> None:
    """Future-proof: незнакомые keys (от ещё не добавленных парсеров)
    не падают, просто не попадают в parser_sources."""
    response = await api_client.post(
        ENDPOINT,
        json={
            "annual_report_years": [2025],
            "source_trail": {"future_key_xyz": "something", "revenue_2025": "FORM_2"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["parser_sources"] == ["form_2"]


@pytest.mark.asyncio
async def test_partial_quarters_in_years_covered_not_full(
    api_client: httpx.AsyncClient,
) -> None:
    """Year с partial квартальными данными виден в years_covered, но не
    повышает full_years / level."""
    response = await api_client.post(
        ENDPOINT,
        json={
            "annual_report_years": [2025],
            "partial_quarter_years": [2023],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["years_covered"] == [2023, 2025]
    assert body["full_years"] == [2025]
    assert body["level"] == "minimal"


@pytest.mark.asyncio
async def test_extra_fields_rejected(api_client: httpx.AsyncClient) -> None:
    """Pydantic StrictModel — лишние поля → 422."""
    response = await api_client.post(
        ENDPOINT,
        json={"unknown_field": "x"},
    )
    assert response.status_code == 422
