"""E2E: GET /api/dossier/{id} против real Postgres.

Сценарий: создаём досье через POST /api/manual-input, читаем через
GET /api/dossier/{id}, проверяем структуру ответа (borrower / KPI / chart /
red flags) + 404 на несуществующий UUID.

Override get_session на pg_session — endpoint commit'ит в savepoint, после
теста outer-tx откатывается.
"""

from __future__ import annotations

import re
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

pytestmark = pytest.mark.integration

POST_ENDPOINT = "/api/manual-input"
GET_ENDPOINT_TEMPLATE = "/api/dossier/{dossier_id}"
BORROWER_INN = "100000888"


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


def _borrower() -> dict[str, Any]:
    return {
        "inn": BORROWER_INN,
        "name": "ООО «E2E Досье»",
        "legal_form": "llc",
        "registration_date": "2019-03-15",
        "director_name": "Иванов А.А.",
        "director_appointed_at": "2021-06-01",
        "okved_main": "46.49",
        "registered_address": "Ташкент, ул. Тестовая 1",
    }


def _payload_with_12_months() -> dict[str, Any]:
    """Полный POST-payload: 12 monthly_turnover чтобы revenue_ltm посчитался."""
    monthly = [
        {"month_start": f"2025-{m:02d}-01", "revenue": _money("1000000000")}
        for m in range(1, 13)
    ]
    return {
        "borrower": _borrower(),
        "as_of": "2026-05-08",
        "monthly_turnover": monthly,
    }


async def test_get_dossier_returns_full_view(
    api_client: httpx.AsyncClient,
) -> None:
    """Happy path: создаём через POST, читаем через GET, проверяем структуру."""
    create = await api_client.post(POST_ENDPOINT, json=_payload_with_12_months())
    assert create.status_code == 200, create.text
    dossier_id = create.json()["dossier_id"]

    r = await api_client.get(GET_ENDPOINT_TEMPLATE.format(dossier_id=dossier_id))
    assert r.status_code == 200, r.text
    body = r.json()

    # Skeleton ответа: совпадает с DossierViewResponse pydantic-схемой.
    assert body["dossier_id"] == dossier_id
    assert body["borrower_inn_masked"] == "XXXXX0888"
    assert body["as_of"] == "2026-05-08"
    # ADR-0024 Session 2: +OFF_BALANCE_COMMITMENTS/CASH_FLOW_QUALITY
    assert body["rules_evaluated"] == 24

    # Score: и raw, и display одновременно (правило A).
    risk = body["risk_score"]
    assert "score" in risk and "display_score" in risk
    assert risk["display_score"] == 100 - risk["score"]
    assert risk["recommendation"] in ("approve", "review", "reject")

    # Borrower: реквизиты восстановлены без потерь.
    borr = body["borrower"]
    assert borr["inn"] == BORROWER_INN
    assert borr["name"] == "ООО «E2E Досье»"
    assert borr["legal_form"] == "llc"
    assert borr["registration_date"] == "2019-03-15"

    # Application: id вида BR-YYYY-NNNN (T1.1: monotonic sequence),
    # status пока всегда in_review.
    app = body["application"]
    assert re.fullmatch(r"BR-\d{4}-\d{4}", app["id"]), f"unexpected case_id: {app['id']}"
    assert app["status"] == "in_review"

    # KPI: revenue_ltm посчитан (12 мес × 1B = 12B); вторичные None.
    kpis = body["kpis"]
    assert kpis["revenue_ltm"] is not None
    assert kpis["revenue_ltm"]["unit"] == "UZS"
    assert kpis["revenue_ltm"]["value"] == "12000000000"
    assert len(kpis["revenue_ltm"]["sparkline"]) == 12
    assert kpis["ebit"] is None
    assert kpis["roe"] is None
    assert kpis["debt_to_ebit"] is None

    # Monthly chart: 12 точек по 1B каждый, в хронологическом порядке.
    chart = body["monthly_revenue_24m"]
    assert len(chart) == 12
    assert chart[0]["month"] == "2025-01"
    assert chart[-1]["month"] == "2025-12"
    assert all(p["revenue"] == "1000000000" for p in chart)


async def test_get_dossier_with_no_monthly_data_has_empty_chart_and_no_kpis(
    api_client: httpx.AsyncClient,
) -> None:
    """Degraded path: без monthly_turnover чарт пустой, revenue_ltm=None."""
    payload: dict[str, Any] = {
        "borrower": _borrower(),
        "as_of": "2026-05-08",
    }
    create = await api_client.post(POST_ENDPOINT, json=payload)
    assert create.status_code == 200, create.text
    dossier_id = create.json()["dossier_id"]

    r = await api_client.get(GET_ENDPOINT_TEMPLATE.format(dossier_id=dossier_id))
    assert r.status_code == 200
    body = r.json()

    assert body["kpis"]["revenue_ltm"] is None
    assert body["monthly_revenue_24m"] == []


async def test_get_dossier_returns_404_for_unknown_id(
    api_client: httpx.AsyncClient,
) -> None:
    unknown = UUID("00000000-0000-0000-0000-000000000000")
    r = await api_client.get(GET_ENDPOINT_TEMPLATE.format(dossier_id=str(unknown)))
    assert r.status_code == 404
    assert r.json()["detail"] == "Досье не найдено"


async def test_get_dossier_returns_422_for_malformed_uuid(
    api_client: httpx.AsyncClient,
) -> None:
    """Path-param не парсится → FastAPI отдаёт 422, не доходит до use case."""
    r = await api_client.get("/api/dossier/not-a-uuid")
    assert r.status_code == 422


# ----------- CA-035b: GET /api/dossier/{id}/readiness -------------------------


async def test_get_dossier_readiness_happy_path(
    api_client: httpx.AsyncClient,
) -> None:
    """Создаём досье, читаем readiness — манипуляции с DataReadinessResponse."""
    create = await api_client.post(POST_ENDPOINT, json=_payload_with_12_months())
    assert create.status_code == 200, create.text
    dossier_id = create.json()["dossier_id"]

    r = await api_client.get(f"/api/dossier/{dossier_id}/readiness")
    assert r.status_code == 200, r.text
    body = r.json()

    # Skeleton: совпадает с DataReadinessResponse.
    assert body["level"] in ("insufficient", "minimal", "standard", "comprehensive")
    assert isinstance(body["years_covered"], list)
    assert isinstance(body["full_years"], list)
    assert isinstance(body["missing_capabilities"], list)
    # MANUAL добавляется всегда (досье существует → данные были введены).
    assert "manual" in body["parser_sources"]
    # confidence_score — строка-Decimal, не None.
    assert isinstance(body["confidence_score"], str)


async def test_get_dossier_readiness_returns_404_for_unknown_id(
    api_client: httpx.AsyncClient,
) -> None:
    unknown = UUID("00000000-0000-0000-0000-000000000000")
    r = await api_client.get(f"/api/dossier/{unknown}/readiness")
    assert r.status_code == 404
    assert r.json()["detail"] == "Досье не найдено"
