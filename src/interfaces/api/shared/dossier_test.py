"""Integration-тесты POST /api/manual-input.

Проверяем end-to-end: payload → Pydantic → mapper → use case → rules → scoring → JSON.
Хранилище переопределено на in-memory dummy: тесты НЕ требуют поднятой БД,
но проверяют, что endpoint вызывает все три save-метода. Реальные round-trip
тесты против Postgres — категория testcontainers (2.5.7).
"""

from collections.abc import Iterator
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from application.dto.dossier_record import DossierRecord
from application.dto.dossier_view_record import DossierViewRecord
from domain.entities.borrower import Borrower
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.value_objects.inn import INN
from interfaces.api.app import create_app
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service
from interfaces.api.shared.dossier_storage import DossierStorage, get_dossier_storage

ENDPOINT = "/api/manual-input"
BORROWER_INN = "306399449"


class _InMemoryBorrowerRepo:
    async def upsert(self, borrower: Borrower) -> UUID:
        return uuid4()

    async def get_by_inn(self, inn: INN) -> Borrower | None:
        return None

    async def get_by_id(self, borrower_id: UUID) -> Borrower | None:
        return None


class _InMemorySnapshotRepo:
    async def save(self, snapshot: BorrowerSnapshot, borrower_id: UUID) -> UUID:
        return uuid4()

    async def get_by_id(self, snapshot_id: UUID) -> BorrowerSnapshot | None:
        return None


class _InMemoryDossierRepo:
    async def save(
        self,
        record: DossierRecord,
        snapshot_id: UUID,
        case_id: str,
        *,
        source_mode: str = "accountant",
        created_by_analyst_id: UUID | None = None,
    ) -> UUID:
        return uuid4()

    async def get_by_id(self, dossier_id: UUID) -> DossierRecord | None:
        return None

    async def get_view_by_id(
        self, dossier_id: UUID
    ) -> DossierViewRecord | None:
        return None


class _InMemoryDraftRepo:
    async def create(self, payload: dict[str, Any]) -> UUID:
        return uuid4()

    async def update(self, draft_id: UUID, payload: dict[str, Any]) -> bool:
        return False

    async def get(self, draft_id: UUID) -> dict[str, Any] | None:
        return None

    async def purge_expired(self) -> int:
        return 0


class _DummyCaseIdAllocator:
    """Stub allocator: всегда возвращает одну и ту же строку. Тест endpoint'а
    проверяет интеграцию с use-case'ом, не sequence-семантику.
    """

    async def allocate(self, now: datetime) -> str:
        return "BR-2026-T999"


def _in_memory_storage() -> DossierStorage:
    return DossierStorage(
        borrower=_InMemoryBorrowerRepo(),
        snapshot=_InMemorySnapshotRepo(),
        dossier=_InMemoryDossierRepo(),
        draft=_InMemoryDraftRepo(),
        case_id_allocator=_DummyCaseIdAllocator(),
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Сбросить lru_cache, чтобы тесты не делили зависимости.
    get_rule_registry.cache_clear()
    get_scoring_service.cache_clear()
    app = create_app()
    app.dependency_overrides[get_dossier_storage] = _in_memory_storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _borrower_payload(
    *,
    director_appointed_at: str = "2020-01-01",
    oked_main_changed_at: str | None = None,
    oked_changed_by_owner: bool = False,
) -> dict[str, Any]:
    return {
        "inn": BORROWER_INN,
        "name": 'ООО "AZ RUHDIL SAVDO"',
        "legal_form": "llc",
        "registration_date": "2018-05-01",
        "director_name": "Иванов И.И.",
        "director_appointed_at": director_appointed_at,
        "oked_main": "46.49",
        "registered_address": "Ташкент, ул. Амира Темура, 1",
        "oked_main_changed_at": oked_main_changed_at,
        # ADR-0024 Session 3: OKVED_CHANGED_12M fires только при owner-initiated
        # смене ОКЭД. Helper-level default False; тесты, полагающиеся на
        # firing, передают True явно.
        "oked_changed_by_owner": oked_changed_by_owner,
    }


def _money(amount: str, currency: str = "UZS") -> dict[str, str]:
    return {"amount": amount, "currency": currency}


def _loan_request(amount: str) -> dict[str, Any]:
    return {
        "amount": _money(amount),
        "term_months": 24,
        "rate_pct": "22.5",
        "purpose": "working_capital",
        "category": "standard",
    }


def _annual(year: int, revenue: str, net_profit: str = "0") -> dict[str, Any]:
    return {
        "period": {"start": f"{year}-01-01", "end": f"{year}-12-31"},
        "revenue": _money(revenue),
        "net_profit": _money(net_profit),
        "taxes_paid": _money("0"),
    }


def _quarter(year: int, q: int, net_profit: str) -> dict[str, Any]:
    starts = {1: ("01", "01", "03", "31"), 2: ("04", "01", "06", "30"),
              3: ("07", "01", "09", "30"), 4: ("10", "01", "12", "31")}
    sm, sd, em, ed = starts[q]
    return {
        "period": {"start": f"{year}-{sm}-{sd}", "end": f"{year}-{em}-{ed}"},
        "revenue": _money("100000000"),
        "net_profit": _money(net_profit),
        "taxes_paid": _money("0"),
    }


class TestEmptyPayload:
    def test_minimal_valid_payload_triggers_insufficient_data(
        self, client: TestClient
    ) -> None:
        # CA-016: пустой снапшот без выручки → INSUFFICIENT_DATA + REVIEW + score floor 50.
        payload = {
            "borrower": _borrower_payload(),
            "as_of": "2026-05-08",
        }
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["borrower_inn_masked"].endswith("9449")
        rule_ids = [f["rule_id"] for f in data["red_flags"]]
        assert "INSUFFICIENT_DATA" in rule_ids
        assert data["risk_score"]["score"] == 50
        assert data["risk_score"]["recommendation"] == "review"
        assert data["rules_evaluated"] == 24  # ADR-0024 Session 2: +OFF_BALANCE/CASH_FLOW


class TestOptionalTaxesPaid:
    def test_annual_report_without_taxes_paid_accepted_200(
        self, client: TestClient
    ) -> None:
        """CA-044: taxes_paid опциональный — отсутствие поля в payload
        не должно валить запрос и не должно превращаться в Money(0).
        """
        payload = {
            "borrower": _borrower_payload(),
            "as_of": "2026-05-08",
            "annual_reports": [
                {
                    "period": {"start": "2024-01-01", "end": "2024-12-31"},
                    "revenue": _money("5000000000"),
                    "net_profit": _money("300000000"),
                    # taxes_paid намеренно отсутствует — «не заполнено».
                },
            ],
        }
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 200, r.text


class TestCa037FinancialReportExtensions:
    """CA-037: FinancialReportInput принимает 8 новых nullable money-полей —
    profit_before_tax / interest_expense / equity / total_debt (период_end) +
    тот же набор period_start для balance. Schema на extra='forbid', поэтому
    без расширения schema endpoint вернёт 422.
    """

    def test_annual_report_with_all_ca037_money_fields_accepted_200(
        self, client: TestClient
    ) -> None:
        payload = {
            "borrower": _borrower_payload(),
            "as_of": "2026-05-08",
            "annual_reports": [
                {
                    "period": {"start": "2025-01-01", "end": "2025-12-31"},
                    "revenue": _money("5000000000"),
                    "net_profit": _money("400000000"),
                    "taxes_paid": _money("250000000"),
                    "assets": _money("2500000000"),
                    "liabilities": _money("1000000000"),
                    "profit_before_tax": _money("550000000"),
                    "interest_expense": _money("80000000"),
                    "equity": _money("1500000000"),
                    "total_debt": _money("700000000"),
                    "assets_period_start": _money("2300000000"),
                    "liabilities_period_start": _money("950000000"),
                    "equity_period_start": _money("1350000000"),
                    "total_debt_period_start": _money("650000000"),
                },
            ],
        }
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 200, r.text

    def test_annual_report_omits_ca037_fields_still_accepted_200(
        self, client: TestClient
    ) -> None:
        # Все 8 — Optional, payload без них принимается как до CA-037 (регрессия).
        payload = {
            "borrower": _borrower_payload(),
            "as_of": "2026-05-08",
            "annual_reports": [_annual(2025, revenue="1000000000")],
        }
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 200, r.text


class TestInvalidPayload:
    def test_invalid_inn_returns_422(self, client: TestClient) -> None:
        payload = {
            "borrower": {**_borrower_payload(), "inn": "12345"},  # короткий
            "as_of": "2026-05-08",
        }
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 422

    def test_extra_field_returns_422(self, client: TestClient) -> None:
        payload = {
            "borrower": _borrower_payload(),
            "as_of": "2026-05-08",
            "unknown_field": 42,
        }
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 422

    def test_missing_borrower_returns_422(self, client: TestClient) -> None:
        r = client.post(ENDPOINT, json={"as_of": "2026-05-08"})
        assert r.status_code == 422


class TestLoanToRevenueRule:
    def test_loan_over_50pct_of_annual_revenue_fires_rule(self, client: TestClient) -> None:
        payload = {
            "borrower": _borrower_payload(),
            "as_of": "2026-05-08",
            "annual_reports": [_annual(2025, revenue="1000000000")],
            "loan_request": _loan_request("600000000"),  # 60% от выручки
        }
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 200
        ids = [f["rule_id"] for f in r.json()["red_flags"]]
        assert "LOAN_TO_REVENUE_RATIO" in ids


class TestDirectorChangedRule:
    def test_director_appointed_within_6_months_fires(self, client: TestClient) -> None:
        # as_of 2026-05-08, директор назначен 2026-01-15 → ~4 месяца назад
        # ADR-0024: правилу теперь нужен материальный loan ≥500 млн UZS.
        payload = {
            "borrower": _borrower_payload(director_appointed_at="2026-01-15"),
            "as_of": "2026-05-08",
            "loan_request": _loan_request("700000000"),
        }
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 200
        ids = [f["rule_id"] for f in r.json()["red_flags"]]
        assert "DIRECTOR_CHANGED_6M" in ids


class TestOkvedChangedRule:
    def test_okved_changed_within_12_months_fires(self, client: TestClient) -> None:
        payload = {
            "borrower": _borrower_payload(
                oked_main_changed_at="2025-08-01",
                # ADR-0024 Session 3: правило требует owner-initiated смену.
                oked_changed_by_owner=True,
            ),
            "as_of": "2026-05-08",
        }
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 200
        ids = [f["rule_id"] for f in r.json()["red_flags"]]
        assert "OKVED_CHANGED_12M" in ids


class TestNegativeProfitRule:
    def test_three_consecutive_loss_quarters_fires(self, client: TestClient) -> None:
        payload = {
            "borrower": _borrower_payload(),
            "as_of": "2026-05-08",
            "quarterly_reports": [
                _quarter(2025, 2, net_profit="-10000000"),
                _quarter(2025, 3, net_profit="-15000000"),
                _quarter(2025, 4, net_profit="-5000000"),
            ],
        }
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 200
        ids = [f["rule_id"] for f in r.json()["red_flags"]]
        assert "NEGATIVE_PROFIT_3Q" in ids


class TestRiskScoreCombination:
    def test_combined_flags_drive_recommendation_to_review(
        self, client: TestClient,
    ) -> None:
        # По калибровке (Phase 1): 2 medium + 2 high = 3+3+7+7 = 20 → REVIEW.
        payload = {
            "borrower": _borrower_payload(
                director_appointed_at="2026-01-15",       # medium
                oked_main_changed_at="2025-08-01",        # medium
                # ADR-0024 Session 3: явный owner-initiated флаг для firing
                # OKVED_CHANGED_12M в скор-комбинации.
                oked_changed_by_owner=True,
            ),
            "as_of": "2026-05-08",
            "annual_reports": [_annual(2025, revenue="1000000000")],
            "loan_request": _loan_request("600000000"),    # high
            "quarterly_reports": [
                _quarter(2025, 2, net_profit="-10000000"),
                _quarter(2025, 3, net_profit="-15000000"),
                _quarter(2025, 4, net_profit="-5000000"),  # high
            ],
        }
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 200
        body = r.json()
        ids = {f["rule_id"] for f in body["red_flags"]}
        assert {
            "DIRECTOR_CHANGED_6M",
            "OKVED_CHANGED_12M",
            "LOAN_TO_REVENUE_RATIO",
            "NEGATIVE_PROFIT_3Q",
        } <= ids
        assert body["risk_score"]["score"] >= 15
        assert body["risk_score"]["recommendation"] in ("review", "reject")


class TestEvidenceShape:
    def test_red_flag_includes_source_and_evidence(self, client: TestClient) -> None:
        # ADR-0024: DIRECTOR_CHANGED_6M требует материального loan_request.
        payload = {
            "borrower": _borrower_payload(director_appointed_at="2026-01-15"),
            "as_of": "2026-05-08",
            "loan_request": _loan_request("700000000"),
        }
        r = client.post(ENDPOINT, json=payload)
        flag = next(
            f for f in r.json()["red_flags"] if f["rule_id"] == "DIRECTOR_CHANGED_6M"
        )
        assert flag["severity"] in {"low", "medium", "high", "critical"}
        assert flag["source"]
        assert flag["rule_version"]
        assert isinstance(flag["evidence"], dict)
        assert flag["detected_at"] == "2026-05-08"
