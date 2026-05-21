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
            oked_main="62.01",
            registered_address="Ташкент",
        ),
        as_of=date(2026, 5, 8),
        annual_reports=list(reports),
    )


# ADR-0024: материальный порог prev > 200 млн UZS.
M = 1_000_000  # 1 млн UZS = 1M (короткая ссылка для читаемости тестов)


class TestRevenueDropYoy50:
    def test_fires_when_revenue_drops_60pct(self) -> None:
        # 500M → 200M = −60% YoY, prev > 200M порог.
        ev = revenue_drop_yoy_50(_snapshot(_annual(2024, 500 * M), _annual(2025, 200 * M)))
        assert ev is not None

    def test_silent_when_drop_only_20pct(self) -> None:
        assert (
            revenue_drop_yoy_50(_snapshot(_annual(2024, 500 * M), _annual(2025, 400 * M))) is None
        )

    def test_silent_at_exactly_50pct(self) -> None:
        # 500M → 250M = ровно −50%, boundary inclusive (>=) silent.
        assert (
            revenue_drop_yoy_50(_snapshot(_annual(2024, 500 * M), _annual(2025, 250 * M))) is None
        )

    def test_silent_with_only_one_annual_report(self) -> None:
        assert revenue_drop_yoy_50(_snapshot(_annual(2025, 500 * M))) is None

    def test_silent_when_growing(self) -> None:
        assert (
            revenue_drop_yoy_50(_snapshot(_annual(2024, 500 * M), _annual(2025, 750 * M))) is None
        )

    def test_silent_when_previous_year_zero(self) -> None:
        assert revenue_drop_yoy_50(_snapshot(_annual(2024, 0), _annual(2025, 0))) is None

    def test_silent_when_prev_below_material_threshold(self) -> None:
        # ADR-0024: prev=100 млн (< 200M) — silent даже при −60% drop
        assert (
            revenue_drop_yoy_50(_snapshot(_annual(2024, 100 * M), _annual(2025, 40 * M))) is None
        )

    def test_fires_at_material_boundary(self) -> None:
        # ADR-0024: prev=201 млн (>200M) — fires
        ev = revenue_drop_yoy_50(_snapshot(_annual(2024, 201 * M), _annual(2025, 50 * M)))
        assert ev is not None
