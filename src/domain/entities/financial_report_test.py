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

    def test_ca037_income_statement_extensions_default_none(self) -> None:
        # CA-037: profit_before_tax / interest_expense — компоненты EBIT
        r = _annual_2025()
        assert r.profit_before_tax is None
        assert r.interest_expense is None

    def test_ca037_balance_period_end_extensions_default_none(self) -> None:
        # CA-037: equity / total_debt на конец периода — компоненты ROE и Debt-to-EBIT
        r = _annual_2025()
        assert r.equity is None
        assert r.total_debt is None

    def test_ca037_balance_period_start_extensions_default_none(self) -> None:
        # CA-037: period_start снимки для расчёта equity_avg в ROE.
        # Семантика: balance на начало того же периода (DateRange.start);
        # обычно приходят вместе с period_end через FORM_1 (две колонки).
        r = _annual_2025()
        assert r.assets_period_start is None
        assert r.liabilities_period_start is None
        assert r.equity_period_start is None
        assert r.total_debt_period_start is None

    def test_ca037_full_construction_round_trip(self) -> None:
        # Все 8 новых полей принимаются вместе с базовыми; entity frozen — round-trip
        # через сравнение значений.
        r = FinancialReport(
            period=DateRange(date(2025, 1, 1), date(2025, 12, 31)),
            revenue=Money(Decimal("5000000000"), UZS),
            net_profit=Money(Decimal("400000000"), UZS),
            taxes_paid=Money(Decimal("250000000"), UZS),
            vat_declared=Money(Decimal("600000000"), UZS),
            assets=Money(Decimal("2500000000"), UZS),
            liabilities=Money(Decimal("1000000000"), UZS),
            profit_before_tax=Money(Decimal("550000000"), UZS),
            interest_expense=Money(Decimal("80000000"), UZS),
            equity=Money(Decimal("1500000000"), UZS),
            total_debt=Money(Decimal("700000000"), UZS),
            assets_period_start=Money(Decimal("2300000000"), UZS),
            liabilities_period_start=Money(Decimal("950000000"), UZS),
            equity_period_start=Money(Decimal("1350000000"), UZS),
            total_debt_period_start=Money(Decimal("650000000"), UZS),
        )
        assert r.profit_before_tax is not None
        assert r.profit_before_tax.amount == Decimal("550000000")
        assert r.interest_expense is not None
        assert r.interest_expense.amount == Decimal("80000000")
        assert r.equity is not None and r.equity.amount == Decimal("1500000000")
        assert r.total_debt is not None and r.total_debt.amount == Decimal("700000000")
        assert (
            r.equity_period_start is not None
            and r.equity_period_start.amount == Decimal("1350000000")
        )
        assert (
            r.total_debt_period_start is not None
            and r.total_debt_period_start.amount == Decimal("650000000")
        )
        assert (
            r.assets_period_start is not None
            and r.assets_period_start.amount == Decimal("2300000000")
        )
        assert (
            r.liabilities_period_start is not None
            and r.liabilities_period_start.amount == Decimal("950000000")
        )

    def test_quarterly_report(self) -> None:
        # NEGATIVE_PROFIT_3Q использует кварталы
        q1 = FinancialReport(
            period=DateRange(date(2026, 1, 1), date(2026, 3, 31)),
            revenue=Money(0, UZS),
            net_profit=Money(Decimal("-50000"), UZS),
            taxes_paid=Money(0, UZS),
        )
        assert q1.net_profit.amount < Decimal("0")
