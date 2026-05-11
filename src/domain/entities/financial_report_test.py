"""FinancialReport: годовой/квартальный отчёт с выручкой, прибылью, налогами."""

from datetime import date
from decimal import Decimal

from domain.entities.financial_report import FinancialReport
from domain.value_objects.balance_snapshot import BalanceSnapshot
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
        # CA-047: balance_end / balance_start — sub-entity BalanceSnapshot
        # вместо 8 flat полей; default None означает «FORM_1 не загружен».
        r = _annual_2025()
        assert r.balance_end is None
        assert r.balance_start is None

    def test_ca037_income_statement_extensions_default_none(self) -> None:
        # CA-037: profit_before_tax / interest_expense — компоненты EBIT
        r = _annual_2025()
        assert r.profit_before_tax is None
        assert r.interest_expense is None

    def test_ca047_full_construction_round_trip(self) -> None:
        # CA-047: balance_end + balance_start как BalanceSnapshot.
        r = FinancialReport(
            period=DateRange(date(2025, 1, 1), date(2025, 12, 31)),
            revenue=Money(Decimal("5000000000"), UZS),
            net_profit=Money(Decimal("400000000"), UZS),
            taxes_paid=Money(Decimal("250000000"), UZS),
            vat_declared=Money(Decimal("600000000"), UZS),
            profit_before_tax=Money(Decimal("550000000"), UZS),
            interest_expense=Money(Decimal("80000000"), UZS),
            balance_end=BalanceSnapshot(
                assets=Money(Decimal("2500000000"), UZS),
                liabilities=Money(Decimal("1000000000"), UZS),
                equity=Money(Decimal("1500000000"), UZS),
                total_debt=Money(Decimal("700000000"), UZS),
            ),
            balance_start=BalanceSnapshot(
                assets=Money(Decimal("2300000000"), UZS),
                liabilities=Money(Decimal("950000000"), UZS),
                equity=Money(Decimal("1350000000"), UZS),
                total_debt=Money(Decimal("650000000"), UZS),
            ),
        )
        assert r.profit_before_tax is not None
        assert r.profit_before_tax.amount == Decimal("550000000")
        assert r.interest_expense is not None
        assert r.interest_expense.amount == Decimal("80000000")
        assert r.balance_end is not None
        assert r.balance_end.equity is not None
        assert r.balance_end.equity.amount == Decimal("1500000000")
        assert r.balance_end.total_debt is not None
        assert r.balance_end.total_debt.amount == Decimal("700000000")
        assert r.balance_end.assets is not None
        assert r.balance_end.assets.amount == Decimal("2500000000")
        assert r.balance_end.liabilities is not None
        assert r.balance_end.liabilities.amount == Decimal("1000000000")
        assert r.balance_start is not None
        assert r.balance_start.equity is not None
        assert r.balance_start.equity.amount == Decimal("1350000000")
        assert r.balance_start.total_debt is not None
        assert r.balance_start.total_debt.amount == Decimal("650000000")
        assert r.balance_start.assets is not None
        assert r.balance_start.assets.amount == Decimal("2300000000")
        assert r.balance_start.liabilities is not None
        assert r.balance_start.liabilities.amount == Decimal("950000000")

    def test_ca047_partial_balance_snapshot(self) -> None:
        # CA-047: BalanceSnapshot допускает частичное заполнение —
        # FORM_1 может прислать только equity без assets/liabilities.
        snap = BalanceSnapshot(equity=Money(Decimal("100"), UZS))
        assert snap.assets is None
        assert snap.liabilities is None
        assert snap.equity is not None
        assert snap.total_debt is None
        assert snap.is_empty() is False

    def test_ca047_empty_balance_snapshot(self) -> None:
        # Пустой snapshot (`is_empty()=True`) — все 4 поля None;
        # хелпер используется в mapper-ах для отсечения no-op snapshots.
        snap = BalanceSnapshot()
        assert snap.is_empty() is True

    def test_quarterly_report(self) -> None:
        # NEGATIVE_PROFIT_3Q использует кварталы
        q1 = FinancialReport(
            period=DateRange(date(2026, 1, 1), date(2026, 3, 31)),
            revenue=Money(0, UZS),
            net_profit=Money(Decimal("-50000"), UZS),
            taxes_paid=Money(0, UZS),
        )
        assert q1.net_profit.amount < Decimal("0")
