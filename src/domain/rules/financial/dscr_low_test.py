"""DSCR_LOW unit tests (ADR-0024)."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.rules.financial.dscr_low import dscr_low
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


def _annual(
    *,
    revenue: int = 10_000_000_000,
    net_profit: int = 1_000_000_000,
    profit_before_tax: int | None = None,
    interest_expense: int | None = None,
    depreciation_amortization: int | None = None,
    operating_cash_flow: int | None = None,
) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(2025, 1, 1), date(2025, 12, 31)),
        revenue=Money(Decimal(revenue), UZS),
        net_profit=Money(Decimal(net_profit), UZS),
        profit_before_tax=(
            Money(Decimal(profit_before_tax), UZS) if profit_before_tax is not None else None
        ),
        interest_expense=(
            Money(Decimal(interest_expense), UZS) if interest_expense is not None else None
        ),
        depreciation_amortization=(
            Money(Decimal(depreciation_amortization), UZS)
            if depreciation_amortization is not None
            else None
        ),
        operating_cash_flow=(
            Money(Decimal(operating_cash_flow), UZS) if operating_cash_flow is not None else None
        ),
    )


def _loan(amount: int = 1_200_000_000, term_months: int = 12) -> LoanRequest:
    return LoanRequest(
        amount=Money(Decimal(amount), UZS),
        term_months=term_months,
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
            oked_main="01.16",
            registered_address="Ташкент",
        ),
        as_of=date(2026, 5, 19),
        annual_reports=list(reports) if reports else [],
        loan_request=loan,
    )


class TestDscrLow:
    def test_fires_when_dscr_below_threshold_via_ocf(self) -> None:
        # OCF=1.0B, interest=100M, principal_annual=1B → debt service 1.1B
        # DSCR = 1.0 / 1.1 ≈ 0.91 < 1.3 → fires
        ev = dscr_low(
            _snapshot(
                loan=_loan(amount=1_000_000_000, term_months=12),
                reports=[_annual(operating_cash_flow=1_000_000_000, interest_expense=100_000_000)],
            )
        )
        assert ev is not None
        assert ev.evidence["numerator_source"] == "OCF"
        assert Decimal(ev.evidence["dscr"]) < Decimal("1.3")

    def test_silent_when_dscr_at_threshold(self) -> None:
        # OCF=2.6B, interest=100M, principal_annual=1.9B → debt service 2.0B
        # DSCR = 2.6/2.0 = 1.30 → silent (>=)
        assert (
            dscr_low(
                _snapshot(
                    loan=_loan(amount=1_900_000_000, term_months=12),
                    reports=[
                        _annual(operating_cash_flow=2_600_000_000, interest_expense=100_000_000)
                    ],
                )
            )
            is None
        )

    def test_silent_when_dscr_high(self) -> None:
        # OCF=5B, debt service ~1.1B → DSCR ~4.5 — здоровое покрытие
        assert (
            dscr_low(
                _snapshot(
                    loan=_loan(amount=1_000_000_000, term_months=12),
                    reports=[
                        _annual(operating_cash_flow=5_000_000_000, interest_expense=100_000_000)
                    ],
                )
            )
            is None
        )

    def test_falls_back_to_ebitda_when_no_ocf(self) -> None:
        # Нет OCF — используем EBITDA = profit_before_tax + interest + D&A
        # EBITDA = 800M + 100M + 200M = 1.1B; debt service = 100M + 1B = 1.1B
        # DSCR = 1.0 → fires
        ev = dscr_low(
            _snapshot(
                loan=_loan(amount=1_000_000_000, term_months=12),
                reports=[
                    _annual(
                        profit_before_tax=800_000_000,
                        interest_expense=100_000_000,
                        depreciation_amortization=200_000_000,
                    )
                ],
            )
        )
        assert ev is not None
        assert ev.evidence["numerator_source"] == "EBITDA"

    def test_falls_back_to_ebit_when_no_da(self) -> None:
        # Нет OCF и D&A — EBIT = profit_before_tax + interest = 800M + 100M = 900M
        # Debt service = 1.1B → DSCR = 0.82 < 1.3 → fires
        ev = dscr_low(
            _snapshot(
                loan=_loan(amount=1_000_000_000, term_months=12),
                reports=[
                    _annual(
                        profit_before_tax=800_000_000,
                        interest_expense=100_000_000,
                    )
                ],
            )
        )
        assert ev is not None
        assert ev.evidence["numerator_source"] == "EBIT"

    def test_silent_when_no_loan_request(self) -> None:
        assert (
            dscr_low(
                _snapshot(
                    loan=None,
                    reports=[_annual(operating_cash_flow=100_000_000, interest_expense=10_000_000)],
                )
            )
            is None
        )

    def test_silent_when_no_annual_reports(self) -> None:
        assert dscr_low(_snapshot(loan=_loan(), reports=[])) is None

    def test_silent_when_no_interest_expense(self) -> None:
        # Без interest_expense знаменатель неполный — best-effort: skip
        assert (
            dscr_low(
                _snapshot(
                    loan=_loan(),
                    reports=[_annual(operating_cash_flow=100_000_000)],
                )
            )
            is None
        )

    def test_silent_when_no_numerator_data(self) -> None:
        # Есть interest, но нет ни OCF, ни profit_before_tax — числителя нет
        assert (
            dscr_low(
                _snapshot(
                    loan=_loan(),
                    reports=[_annual(interest_expense=100_000_000)],
                )
            )
            is None
        )

    def test_uses_latest_annual(self) -> None:
        # Старый год: здоровая ликвидность; latest год: слабая. Берём latest.
        old = FinancialReport(
            period=DateRange(date(2024, 1, 1), date(2024, 12, 31)),
            revenue=Money(Decimal(10_000_000_000), UZS),
            net_profit=Money(Decimal(1_000_000_000), UZS),
            interest_expense=Money(Decimal(10_000_000), UZS),
            operating_cash_flow=Money(Decimal(10_000_000_000), UZS),
        )
        new = FinancialReport(
            period=DateRange(date(2025, 1, 1), date(2025, 12, 31)),
            revenue=Money(Decimal(10_000_000_000), UZS),
            net_profit=Money(Decimal(100_000_000), UZS),
            interest_expense=Money(Decimal(100_000_000), UZS),
            operating_cash_flow=Money(Decimal(500_000_000), UZS),
        )
        ev = dscr_low(
            _snapshot(loan=_loan(amount=1_000_000_000, term_months=12), reports=[old, new])
        )
        assert ev is not None
