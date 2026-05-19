"""FX_MISMATCH_HIGH unit tests (ADR-0024)."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.rules.financial.fx_mismatch import fx_mismatch
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS
USD = Currency.USD


def _annual(
    revenue_currency: Currency = UZS,
    revenue_amount: int = 10_000_000_000,
) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(2025, 1, 1), date(2025, 12, 31)),
        revenue=Money(Decimal(revenue_amount), revenue_currency),
        net_profit=Money(Decimal(500_000_000), revenue_currency),
    )


def _loan(currency: Currency = UZS, amount: int = 1_000_000_000) -> LoanRequest:
    return LoanRequest(
        amount=Money(Decimal(amount), currency),
        term_months=36,
        rate_pct=Decimal("18.0"),
        purpose="working_capital",
        category="msb",
    )


def _snapshot(
    *,
    loan: LoanRequest | None,
    reports: list[FinancialReport] | None = None,
) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=Borrower(
            inn=INN("123456789"),
            name="ООО",
            legal_form=LegalForm.LLC,
            registration_date=date(2020, 1, 1),
            director_name="Иванов",
            director_appointed_at=date(2020, 1, 1),
            okved_main="62.01",
            registered_address="Ташкент",
        ),
        as_of=date(2026, 5, 19),
        annual_reports=list(reports) if reports else [],
        loan_request=loan,
    )


class TestFxMismatch:
    def test_fires_when_usd_loan_uzs_revenue(self) -> None:
        ev = fx_mismatch(_snapshot(loan=_loan(currency=USD), reports=[_annual(UZS)]))
        assert ev is not None
        assert ev.evidence["loan_currency"] == "USD"
        assert ev.evidence["revenue_currency"] == "UZS"
        assert "валютный риск" in ev.message
        assert "valyuta tavakkalligi" in ev.message_uz

    def test_silent_when_same_currency(self) -> None:
        assert fx_mismatch(_snapshot(loan=_loan(UZS), reports=[_annual(UZS)])) is None

    def test_silent_when_usd_loan_usd_revenue(self) -> None:
        # Естественный hedge: и доход, и долг в одной валюте.
        assert fx_mismatch(_snapshot(loan=_loan(USD), reports=[_annual(USD)])) is None

    def test_silent_when_no_loan(self) -> None:
        assert fx_mismatch(_snapshot(loan=None, reports=[_annual(UZS)])) is None

    def test_silent_when_no_annual_reports(self) -> None:
        assert fx_mismatch(_snapshot(loan=_loan(USD), reports=[])) is None

    def test_uses_latest_annual_when_multiple(self) -> None:
        # Старый отчёт в USD (естественный hedge), новый в UZS — fires на latest.
        old = FinancialReport(
            period=DateRange(date(2024, 1, 1), date(2024, 12, 31)),
            revenue=Money(Decimal(10_000_000_000), USD),
            net_profit=Money(Decimal(500_000_000), USD),
        )
        new = FinancialReport(
            period=DateRange(date(2025, 1, 1), date(2025, 12, 31)),
            revenue=Money(Decimal(10_000_000_000), UZS),
            net_profit=Money(Decimal(500_000_000), UZS),
        )
        ev = fx_mismatch(_snapshot(loan=_loan(USD), reports=[old, new]))
        assert ev is not None
        assert ev.evidence["revenue_currency"] == "UZS"
