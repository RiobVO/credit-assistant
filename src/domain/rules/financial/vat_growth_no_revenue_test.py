"""VAT_GROWTH_NO_REVENUE: рост НДС-обязательств при стагнирующей выручке."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.rules.financial.vat_growth_no_revenue import vat_growth_no_revenue
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


def _months(*pairs: tuple[int, int | None]) -> list[MonthlyTurnover]:
    out: list[MonthlyTurnover] = []
    for i, (rev, vat) in enumerate(pairs):
        out.append(
            MonthlyTurnover(
                month_start=date(2026, i + 1, 1),
                revenue=Money(Decimal(rev), UZS),
                vat_obligations=Money(Decimal(vat), UZS) if vat is not None else None,
            )
        )
    return out


def _snapshot(*pairs: tuple[int, int | None]) -> BorrowerSnapshot:
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
        monthly_turnover=_months(*pairs),
    )


class TestVatGrowthNoRevenue:
    def test_fires_when_vat_doubles_revenue_flat(self) -> None:
        ev = vat_growth_no_revenue(_snapshot((1000, 100), (1000, 150), (1000, 200)))
        assert ev is not None

    def test_silent_when_revenue_grows_with_vat(self) -> None:
        # VAT растёт ровно с выручкой — это норма
        assert vat_growth_no_revenue(_snapshot((1000, 100), (1500, 150), (2000, 200))) is None

    def test_silent_when_vat_grows_under_threshold(self) -> None:
        # VAT 100 → 105 (5%): рост слабый, не флаг
        assert vat_growth_no_revenue(_snapshot((1000, 100), (1000, 102), (1000, 105))) is None

    def test_silent_when_no_vat_data(self) -> None:
        assert vat_growth_no_revenue(_snapshot((1000, None), (1000, None), (1000, None))) is None

    def test_silent_when_less_than_3_months(self) -> None:
        assert vat_growth_no_revenue(_snapshot((1000, 100), (1000, 200))) is None
