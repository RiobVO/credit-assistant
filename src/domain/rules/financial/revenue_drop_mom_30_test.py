"""REVENUE_DROP_MOM_30: падение выручки >30% МоМ два месяца подряд."""

from datetime import date

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.rules.financial.revenue_drop_mom_30 import revenue_drop_mom_30
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("123456789"),
        name="ООО",
        legal_form=LegalForm.LLC,
        registration_date=date(2020, 1, 1),
        director_name="Иванов",
        director_appointed_at=date(2020, 1, 1),
        okved_main="62.01",
        registered_address="Ташкент",
    )


def _snapshot(*revenues: int) -> BorrowerSnapshot:
    months = [
        MonthlyTurnover(
            month_start=date(2026, i + 1, 1),
            revenue=Money(rev, UZS),
        )
        for i, rev in enumerate(revenues)
    ]
    return BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, len(revenues) + 1, 1) if revenues else date(2026, 5, 8),
        monthly_turnover=months,
    )


class TestRevenueDropMom30:
    def test_fires_when_two_consecutive_drops_over_30pct(self) -> None:
        # 100 → 60 (-40%) → 35 (-42%)
        ev = revenue_drop_mom_30(_snapshot(100, 60, 35))
        assert ev is not None

    def test_silent_when_only_one_drop(self) -> None:
        # 100 → 60 (-40%) → 70 (+17%) — рост обратно
        assert revenue_drop_mom_30(_snapshot(100, 60, 70)) is None

    def test_silent_when_less_than_3_months_data(self) -> None:
        assert revenue_drop_mom_30(_snapshot(100, 50)) is None

    def test_silent_at_exactly_30pct_drop(self) -> None:
        # Ровно -30% → silent (>30% строго)
        assert revenue_drop_mom_30(_snapshot(100, 70, 49)) is None

    def test_fires_just_above_30pct(self) -> None:
        # -31% → -31%
        ev = revenue_drop_mom_30(_snapshot(100, 69, 47))
        assert ev is not None

    def test_silent_when_growing(self) -> None:
        assert revenue_drop_mom_30(_snapshot(100, 120, 130)) is None

    def test_silent_when_zero_baseline(self) -> None:
        # Деление на 0 → silent (некорректные данные, не правилом ловить)
        assert revenue_drop_mom_30(_snapshot(0, 0, 0)) is None
