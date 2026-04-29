"""LOW_MARGIN_HIGH_TURNOVER: маржа <5% при выручке >5 млрд сум."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.rules.financial.low_margin_high_turnover import low_margin_high_turnover
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


def _annual(revenue: int, profit: int) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(2025, 1, 1), date(2025, 12, 31)),
        revenue=Money(Decimal(revenue), UZS),
        net_profit=Money(Decimal(profit), UZS),
        taxes_paid=Money(0, UZS),
    )


def _snapshot(*reports: FinancialReport) -> BorrowerSnapshot:
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
        as_of=date(2026, 5, 8),
        annual_reports=list(reports),
    )


B = 1_000_000_000


class TestLowMarginHighTurnover:
    def test_fires_when_high_turnover_low_margin(self) -> None:
        # 10 млрд выручка, 200 млн прибыль → маржа 2%
        ev = low_margin_high_turnover(_snapshot(_annual(10 * B, 200_000_000)))
        assert ev is not None

    def test_silent_when_high_margin(self) -> None:
        # 10 млрд, 600 млн прибыль → 6% маржа — норма
        assert low_margin_high_turnover(_snapshot(_annual(10 * B, 600_000_000))) is None

    def test_silent_when_low_turnover(self) -> None:
        # 3 млрд: ниже порога, маржа неважна
        assert low_margin_high_turnover(_snapshot(_annual(3 * B, 10_000_000))) is None

    def test_silent_at_exactly_5_billion(self) -> None:
        # >5 млрд строго, ровно 5 — silent
        assert low_margin_high_turnover(_snapshot(_annual(5 * B, 100_000_000))) is None

    def test_silent_with_no_annual_reports(self) -> None:
        assert low_margin_high_turnover(_snapshot()) is None

    def test_silent_when_revenue_zero(self) -> None:
        assert low_margin_high_turnover(_snapshot(_annual(0, 0))) is None

    def test_fires_with_negative_margin(self) -> None:
        # Убыток при большом обороте — тоже сигнал
        ev = low_margin_high_turnover(_snapshot(_annual(10 * B, -100_000_000)))
        assert ev is not None

    def test_margin_evidence_rounded_to_4_decimals(self) -> None:
        # CA-021b: маржа из реального деления не должна хранить 20+ знаков.
        # 216_065_371 / 10_000_000_000 = 0.0216065371... → 0.0216 в evidence.
        ev = low_margin_high_turnover(_snapshot(_annual(10 * B, 216_065_371)))
        assert ev is not None
        margin_str = ev.evidence["margin"]
        decimal_part = margin_str.split(".", 1)[1] if "." in margin_str else ""
        assert len(decimal_part) <= 4, f"expected ≤4 decimals, got {margin_str!r}"
        assert margin_str == "0.0216"
