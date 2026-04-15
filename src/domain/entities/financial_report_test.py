"""FinancialReport: годовой/квартальный отчёт с выручкой, прибылью, налогами."""

from datetime import date
from decimal import Decimal

from domain.entities.financial_report import FinancialReport
from domain.value_objects.date_range import DateRange
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


def _annual_2025() -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(2025, 1, 1), date(2025, 12, 31)),
        revenue=Money(Decimal("5000000000"), UZS),
        net_profit=Money(Decimal("400000000"), UZS),
        taxes_paid=Money(Decimal("250000000"), UZS),
        vat_declared=Money(Decimal("600000000"), UZS),
    )


class TestFinancialReportConstruction:
    def test_creates_annual_report(self) -> None:
        r = _annual_2025()
        assert r.period.length_days == 365
        assert r.revenue.amount == Decimal("5000000000")

    def test_optional_balance_fields_default_none(self) -> None:
        r = _annual_2025()
        assert r.assets is None
        assert r.liabilities is None

    def test_quarterly_report(self) -> None:
        # NEGATIVE_PROFIT_3Q использует кварталы
        q1 = FinancialReport(
            period=DateRange(date(2026, 1, 1), date(2026, 3, 31)),
            revenue=Money(0, UZS),
            net_profit=Money(Decimal("-50000"), UZS),
            taxes_paid=Money(0, UZS),
        )
        assert q1.net_profit.amount < Decimal("0")
