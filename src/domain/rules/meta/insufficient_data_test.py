"""Тесты INSUFFICIENT_DATA — defensive default на пустом снапшоте."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.rules.meta.insufficient_data import insufficient_data
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("306399449"),
        name="ООО Пустышка",
        legal_form=LegalForm.LLC,
        registration_date=date(2020, 1, 1),
        director_name="Иванов И.И.",
        director_appointed_at=date(2020, 1, 1),
        okved_main="62.01",
        registered_address="г. Ташкент",
    )


def _uzs(amount: int | str) -> Money:
    return Money(Decimal(amount), Currency.UZS)


def _annual(year: int, revenue: int) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=_uzs(revenue),
        net_profit=_uzs(0),
        taxes_paid=_uzs(0),
    )


def _monthly(year: int, month: int, revenue: int) -> MonthlyTurnover:
    return MonthlyTurnover(month_start=date(year, month, 1), revenue=_uzs(revenue))


class TestFires:
    def test_empty_snapshot_fires(self) -> None:
        snap = BorrowerSnapshot(borrower=_borrower(), as_of=date(2026, 5, 10))
        result = insufficient_data(snap)
        assert result is not None
        assert "Недостаточно данных" in result.message

    def test_all_zero_annual_revenue_fires(self) -> None:
        snap = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 10),
            annual_reports=[_annual(2024, 0), _annual(2025, 0)],
        )
        assert insufficient_data(snap) is not None

    def test_zero_monthly_only_fires(self) -> None:
        snap = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 10),
            monthly_turnover=[_monthly(2026, m, 0) for m in range(1, 6)],
        )
        assert insufficient_data(snap) is not None

    def test_evidence_carries_counts(self) -> None:
        snap = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 10),
            annual_reports=[_annual(2025, 0)],
        )
        result = insufficient_data(snap)
        assert result is not None
        assert result.evidence["annual_reports_count"] == 1
        assert result.evidence["quarterly_reports_count"] == 0
        assert result.evidence["monthly_turnover_count"] == 0


class TestSilent:
    def test_positive_annual_revenue_silent(self) -> None:
        snap = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 10),
            annual_reports=[_annual(2025, 1_000_000)],
        )
        assert insufficient_data(snap) is None

    def test_positive_quarterly_revenue_silent(self) -> None:
        snap = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 10),
            quarterly_reports=[
                FinancialReport(
                    period=DateRange(date(2025, 10, 1), date(2025, 12, 31)),
                    revenue=_uzs(500_000),
                    net_profit=_uzs(0),
                    taxes_paid=_uzs(0),
                ),
            ],
        )
        assert insufficient_data(snap) is None

    def test_positive_monthly_turnover_silent(self) -> None:
        snap = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 10),
            monthly_turnover=[_monthly(2026, 4, 100_000)],
        )
        assert insufficient_data(snap) is None

    def test_mix_zero_and_positive_silent(self) -> None:
        # Хотя бы одна точка выручки положительна → правило молчит.
        snap = BorrowerSnapshot(
            borrower=_borrower(),
            as_of=date(2026, 5, 10),
            annual_reports=[_annual(2024, 0), _annual(2025, 100_000)],
        )
        assert insufficient_data(snap) is None
