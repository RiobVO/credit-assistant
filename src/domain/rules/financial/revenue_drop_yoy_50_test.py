"""REVENUE_DROP_YOY_50: падение годовой выручки >50% YoY."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.rules.financial.revenue_drop_yoy_50 import revenue_drop_yoy_50
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


def _annual(year: int, revenue: int) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=Money(Decimal(revenue), UZS),
        net_profit=Money(0, UZS),
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


class TestRevenueDropYoy50:
    def test_fires_when_revenue_drops_60pct(self) -> None:
        ev = revenue_drop_yoy_50(_snapshot(_annual(2024, 100), _annual(2025, 40)))
        assert ev is not None

    def test_silent_when_drop_only_20pct(self) -> None:
        assert revenue_drop_yoy_50(_snapshot(_annual(2024, 100), _annual(2025, 80))) is None

    def test_silent_at_exactly_50pct(self) -> None:
        assert revenue_drop_yoy_50(_snapshot(_annual(2024, 100), _annual(2025, 50))) is None

    def test_silent_with_only_one_annual_report(self) -> None:
        assert revenue_drop_yoy_50(_snapshot(_annual(2025, 100))) is None

    def test_silent_when_growing(self) -> None:
        assert revenue_drop_yoy_50(_snapshot(_annual(2024, 100), _annual(2025, 150))) is None

    def test_silent_when_previous_year_zero(self) -> None:
        assert revenue_drop_yoy_50(_snapshot(_annual(2024, 0), _annual(2025, 0))) is None
