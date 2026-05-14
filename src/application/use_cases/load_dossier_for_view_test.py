"""Тест use case LoadDossierForView с in-memory fake-репо.

Use case тонкий — проверяем, что:
* при ``None`` от репо use case возвращает ``None`` (404 в endpoint);
* при найденной записи возвращается пара view + посчитанные KPI.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from application.dto.dossier_record import DossierRecord
from application.dto.dossier_view_record import DossierViewRecord
from application.use_cases.load_dossier_for_view import LoadDossierForView
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money


class _FakeRepo:
    def __init__(self, record: DossierViewRecord | None) -> None:
        self._record = record
        self.calls: list[UUID] = []

    async def get_view_by_id(self, dossier_id: UUID) -> DossierViewRecord | None:
        self.calls.append(dossier_id)
        return self._record


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("306399449"),
        name="ООО Тест",
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 1, 1),
        director_name="Иванов И.И.",
        director_appointed_at=date(2020, 1, 1),
        okved_main="62.01",
        registered_address="г. Ташкент",
    )


def _snapshot_with_12_months() -> BorrowerSnapshot:
    monthly = [
        MonthlyTurnover(
            month_start=date(2025, m, 1),
            revenue=Money(Decimal(1_000_000_000), Currency.UZS),
        )
        for m in range(1, 13)
    ]
    return BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 1, 15),
        monthly_turnover=monthly,
    )


def _view_record() -> DossierViewRecord:
    return DossierViewRecord(
        dossier_id=uuid4(),
        dossier=DossierRecord(
            score=12,
            recommendation="approve",
            severity_breakdown={"low": 1},
            red_flags=(),
            rules_version="v1",
            rules_evaluated=17,
        ),
        snapshot=_snapshot_with_12_months(),
        created_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
        case_id="BR-2026-T001",
    )


@pytest.mark.asyncio
async def test_returns_none_when_repo_returns_none() -> None:
    repo = _FakeRepo(None)
    use_case = LoadDossierForView(repo)

    result = await use_case.execute(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_returns_view_with_computed_kpis() -> None:
    record = _view_record()
    repo = _FakeRepo(record)
    use_case = LoadDossierForView(repo)

    result = await use_case.execute(record.dossier_id)

    assert result is not None
    assert result.view is record
    # KPI: 12 месяцев по 1B → revenue_ltm = 12B
    assert result.kpis.revenue_ltm is not None
    assert result.kpis.revenue_ltm.value == Decimal("12000000000")
    # Вторичные KPI degraded (CA-037: компонентов в snapshot нет — annual_reports
    # без profit_before_tax/equity/total_debt).
    assert result.kpis.ebit is None
    assert result.kpis.roe is None
    assert result.kpis.debt_to_ebit is None
    # Monthly chart — 12 точек, тренд и peaks посчитаны
    assert len(result.monthly_revenue_24m) == 12
    assert all(p.revenue == Decimal("1000000000") for p in result.monthly_revenue_24m)
    assert repo.calls == [record.dossier_id]
