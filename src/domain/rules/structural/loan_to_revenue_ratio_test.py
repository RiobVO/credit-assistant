"""LOAN_TO_REVENUE_RATIO: запрашиваемая сумма >40% годовой выручки (ADR-0024)."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.rules.structural.loan_to_revenue_ratio import loan_to_revenue_ratio
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


def _annual(revenue: int) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(2025, 1, 1), date(2025, 12, 31)),
        revenue=Money(revenue, UZS),
        net_profit=Money(0, UZS),
        taxes_paid=Money(0, UZS),
    )


def _loan(amount: int) -> LoanRequest:
    return LoanRequest(
        amount=Money(amount, UZS),
        term_months=24,
        rate_pct=Decimal("22.5"),
        purpose="working_capital",
        category="standard",
    )


def _snapshot(loan: int | None, annual_revenue: int | None) -> BorrowerSnapshot:
    borrower = Borrower(
        inn=INN("123456789"),
        name="ООО",
        legal_form=LegalForm.LLC,
        registration_date=date(2020, 1, 1),
        director_name="Иванов",
        director_appointed_at=date(2020, 1, 1),
        okved_main="62.01",
        registered_address="Ташкент",
    )
    return BorrowerSnapshot(
        borrower=borrower,
        as_of=date(2026, 5, 8),
        loan_request=_loan(loan) if loan is not None else None,
        annual_reports=[_annual(annual_revenue)] if annual_revenue is not None else [],
    )


class TestLoanToRevenueRatio:
    def test_fires_when_loan_equals_revenue(self) -> None:
        ev = loan_to_revenue_ratio(_snapshot(1_000_000_000, 1_000_000_000))
        assert ev is not None
        assert ev.evidence["ratio"] == Decimal("1")

    def test_silent_when_loan_is_10_pct(self) -> None:
        assert loan_to_revenue_ratio(_snapshot(100_000_000, 1_000_000_000)) is None

    def test_silent_at_boundary_40_pct(self) -> None:
        # ADR-0024: >0.4 строго; 0.4 ровно — silent
        assert loan_to_revenue_ratio(_snapshot(400_000_000, 1_000_000_000)) is None

    def test_fires_just_above_40_pct(self) -> None:
        ev = loan_to_revenue_ratio(_snapshot(401_000_000, 1_000_000_000))
        assert ev is not None

    def test_fires_at_50_pct_after_threshold_lowered(self) -> None:
        # Регрессия после ADR-0024: 0.50 теперь fires (раньше boundary).
        ev = loan_to_revenue_ratio(_snapshot(500_000_000, 1_000_000_000))
        assert ev is not None

    def test_silent_when_no_loan_request(self) -> None:
        assert loan_to_revenue_ratio(_snapshot(None, 1_000_000_000)) is None

    def test_silent_when_no_annual_reports(self) -> None:
        assert loan_to_revenue_ratio(_snapshot(1_000_000_000, None)) is None

    def test_fires_when_revenue_zero_and_loan_positive(self) -> None:
        ev = loan_to_revenue_ratio(_snapshot(1_000_000_000, 0))
        assert ev is not None
