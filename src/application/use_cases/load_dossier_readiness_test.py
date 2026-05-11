"""Тесты LoadDossierReadiness use case (CA-035b).

Покрывают:
* None из репо → None из use case (404 в endpoint).
* Happy path: snapshot с разным набором полей → правильный set[ParserSource].
* `infer_parser_sources_from_snapshot` — каждая ветка heuristic'а.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from application.dto.dossier_record import DossierRecord
from application.dto.dossier_view_record import DossierViewRecord
from application.use_cases.load_dossier_readiness import (
    LoadDossierReadiness,
    infer_parser_sources_from_snapshot,
)
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice, InvoiceRole
from domain.entities.vat_period_report import VatPeriodReport
from domain.services.data_readiness import ParserSource
from domain.value_objects.balance_snapshot import BalanceSnapshot
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


class _FakeRepo:
    def __init__(self, record: DossierViewRecord | None) -> None:
        self._record = record

    async def get_view_by_id(self, dossier_id: UUID) -> DossierViewRecord | None:
        return self._record


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("306399449"),
        name="ООО Тест",
        legal_form=LegalForm.LLC,
        registration_date=date(2020, 1, 1),
        director_name="Иванов",
        director_appointed_at=date(2020, 1, 1),
        okved_main="62.01",
        registered_address="Ташкент",
    )


def _annual(
    year: int,
    *,
    profit_before_tax: Money | None = None,
    interest_expense: Money | None = None,
    equity: Money | None = None,
    total_debt: Money | None = None,
    equity_period_start: Money | None = None,
) -> FinancialReport:
    """CA-047: balance fields теперь группируются в BalanceSnapshot. Хелпер
    принимает прежний flat-API для удобства теста, упаковывает внутри.
    """
    balance_end = BalanceSnapshot(equity=equity, total_debt=total_debt)
    balance_start = BalanceSnapshot(equity=equity_period_start)
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=Money(Decimal(1_000_000_000), UZS),
        net_profit=Money(Decimal(100_000_000), UZS),
        taxes_paid=Money(Decimal(0), UZS),
        profit_before_tax=profit_before_tax,
        interest_expense=interest_expense,
        balance_end=balance_end if not balance_end.is_empty() else None,
        balance_start=balance_start if not balance_start.is_empty() else None,
    )


def _snapshot(**kwargs: object) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 8),
        **kwargs,  # type: ignore[arg-type]
    )


def _view(snapshot: BorrowerSnapshot) -> DossierViewRecord:
    return DossierViewRecord(
        dossier_id=uuid4(),
        dossier=DossierRecord(
            score=10,
            recommendation="approve",
            severity_breakdown={},
            red_flags=(),
            rules_version="v1",
            rules_evaluated=19,
        ),
        snapshot=snapshot,
        created_at=datetime(2026, 5, 12, tzinfo=UTC),
    )


# ----------- LoadDossierReadiness use case ------------------------------------


@pytest.mark.asyncio
async def test_returns_none_when_repo_returns_none() -> None:
    """Несуществующий dossier_id → None → endpoint мапит в 404."""
    uc = LoadDossierReadiness(_FakeRepo(None))
    result = await uc.execute(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_returns_readiness_report_when_dossier_found() -> None:
    """Happy path: snapshot с полным FORM_1+FORM_2 даёт STANDARD readiness."""
    snapshot = _snapshot(
        annual_reports=[
            _annual(
                2024,
                profit_before_tax=Money(Decimal(150_000_000), UZS),
                interest_expense=Money(Decimal(20_000_000), UZS),
                equity=Money(Decimal(500_000_000), UZS),
            ),
            _annual(
                2025,
                profit_before_tax=Money(Decimal(170_000_000), UZS),
                interest_expense=Money(Decimal(25_000_000), UZS),
                equity=Money(Decimal(600_000_000), UZS),
            ),
        ],
    )
    uc = LoadDossierReadiness(_FakeRepo(_view(snapshot)))

    report = await uc.execute(uuid4())

    assert report is not None
    assert ParserSource.MANUAL in report.parser_sources
    assert ParserSource.FORM_1 in report.parser_sources
    assert ParserSource.FORM_2 in report.parser_sources
    assert 2024 in report.years_covered
    assert 2025 in report.years_covered


# ----------- infer_parser_sources_from_snapshot -------------------------------
#
# Heuristic: source_trail в БД не хранится, восстанавливаем парсеры из
# присутствия полей. MANUAL добавляется всегда — досье существует, значит
# хоть какие-то данные были.


def test_infer_includes_manual_always() -> None:
    """Даже пустой snapshot даёт MANUAL — досье существует."""
    sources = infer_parser_sources_from_snapshot(_snapshot())
    assert sources == {ParserSource.MANUAL}


def test_infer_detects_form1_via_equity() -> None:
    s = _snapshot(annual_reports=[_annual(2025, equity=Money(Decimal(100_000_000), UZS))])
    sources = infer_parser_sources_from_snapshot(s)
    assert ParserSource.FORM_1 in sources


def test_infer_detects_form1_via_total_debt() -> None:
    s = _snapshot(
        annual_reports=[_annual(2025, total_debt=Money(Decimal(50_000_000), UZS))]
    )
    assert ParserSource.FORM_1 in infer_parser_sources_from_snapshot(s)


def test_infer_detects_form2_via_profit_before_tax() -> None:
    s = _snapshot(
        annual_reports=[
            _annual(2025, profit_before_tax=Money(Decimal(100_000_000), UZS))
        ]
    )
    assert ParserSource.FORM_2 in infer_parser_sources_from_snapshot(s)


def test_infer_detects_form2_via_interest_expense() -> None:
    s = _snapshot(
        annual_reports=[
            _annual(2025, interest_expense=Money(Decimal(10_000_000), UZS))
        ]
    )
    assert ParserSource.FORM_2 in infer_parser_sources_from_snapshot(s)


def test_infer_detects_vat_declaration() -> None:
    s = _snapshot(
        vat_periods=[
            VatPeriodReport(
                period=DateRange(date(2025, 1, 1), date(2025, 1, 31)),
                vat_declared=Money(Decimal(10_000_000), UZS),
            )
        ]
    )
    assert ParserSource.VAT_DECLARATION in infer_parser_sources_from_snapshot(s)


def test_infer_detects_esf_csv_via_invoices() -> None:
    s = _snapshot(
        invoices=[
            Invoice(
                date=date(2025, 6, 1),
                amount=Money(Decimal(1_000_000), UZS),
                our_role=InvoiceRole.SELLER,
                counterparty_inn=INN("100000001"),
                counterparty_name="Контрагент",
            )
        ]
    )
    assert ParserSource.ESF_CSV in infer_parser_sources_from_snapshot(s)


def test_infer_detects_esf_csv_via_esf_seller_vat_total() -> None:
    s = _snapshot(
        vat_periods=[
            VatPeriodReport(
                period=DateRange(date(2025, 1, 1), date(2025, 1, 31)),
                esf_seller_vat_total=Money(Decimal(5_000_000), UZS),
            )
        ]
    )
    assert ParserSource.ESF_CSV in infer_parser_sources_from_snapshot(s)


def test_infer_silent_for_form1_when_only_revenue_present() -> None:
    """Только revenue/net_profit (без CA-037 расширений) → MANUAL only,
    не FORM_1 и не FORM_2."""
    s = _snapshot(annual_reports=[_annual(2025)])  # таки basic fields only
    sources = infer_parser_sources_from_snapshot(s)
    assert sources == {ParserSource.MANUAL}
