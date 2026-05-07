"""MonthlyTurnover: помесячная выручка для MoM правил."""

from datetime import date
from decimal import Decimal

import pytest

from domain.entities.monthly_turnover import MonthlyTurnover
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


class TestMonthlyTurnover:
    def test_creates_with_month_start_and_revenue(self) -> None:
        m = MonthlyTurnover(
            month_start=date(2026, 5, 1),
            revenue=Money(Decimal("100000000"), UZS),
        )
        assert m.month_start == date(2026, 5, 1)
        assert m.revenue.amount == Decimal("100000000")

    def test_rejects_non_first_day_of_month(self) -> None:
        # Соглашение: month_start всегда 1-е число
        with pytest.raises(ValueError, match="first day"):
            MonthlyTurnover(
                month_start=date(2026, 5, 8),
                revenue=Money(0, UZS),
            )

    def test_optional_vat_obligations(self) -> None:
        m = MonthlyTurnover(
            month_start=date(2026, 5, 1),
            revenue=Money(0, UZS),
            vat_obligations=Money(Decimal("12000000"), UZS),
        )
        assert m.vat_obligations is not None
