"""NEGATIVE_PROFIT_3Q: чистая прибыль ≤0 три квартала подряд."""

from datetime import date

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.rules.financial.negative_profit_3q import negative_profit_3q
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS

QUARTERS = [
    DateRange(date(2025, 7, 1), date(2025, 9, 30)),
    DateRange(date(2025, 10, 1), date(2025, 12, 31)),
    DateRange(date(2026, 1, 1), date(2026, 3, 31)),
]


def _quarter(period: DateRange, profit: int) -> FinancialReport:
    return FinancialReport(
        period=period,
        revenue=Money(1, UZS),
        net_profit=Money(profit, UZS),
        taxes_paid=Money(0, UZS),
    )


def _snapshot(*profits: int) -> BorrowerSnapshot:
    reports = [_quarter(QUARTERS[i], p) for i, p in enumerate(profits)]
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
        quarterly_reports=reports,
    )


class TestNegativeProfit3Q:
    def test_fires_three_consecutive_losses(self) -> None:
        ev = negative_profit_3q(_snapshot(-100, -50, -20))
        assert ev is not None

    def test_fires_when_zero_profit_3q(self) -> None:
        # Бриф: «≤0», значит 0 включается
        ev = negative_profit_3q(_snapshot(0, 0, 0))
        assert ev is not None

    def test_silent_when_one_quarter_positive(self) -> None:
        assert negative_profit_3q(_snapshot(-100, 50, -20)) is None

    def test_silent_when_only_two_quarters_data(self) -> None:
        assert negative_profit_3q(_snapshot(-100, -50)) is None

    def test_silent_when_all_positive(self) -> None:
        assert negative_profit_3q(_snapshot(100, 200, 300)) is None

    def test_uses_last_three_quarters_when_more_data(self) -> None:
        # Добавим 4-й квартал с прибылью; правило смотрит только последние 3
        q4 = _quarter(DateRange(date(2026, 4, 1), date(2026, 6, 30)), 1000)
        s = _snapshot(-100, -50, -20)
        s = BorrowerSnapshot(
            borrower=s.borrower,
            as_of=s.as_of,
            quarterly_reports=[*s.quarterly_reports, q4],
        )
        # Последние 3: -50, -20, +1000 — НЕ три убытка подряд
        assert negative_profit_3q(s) is None
