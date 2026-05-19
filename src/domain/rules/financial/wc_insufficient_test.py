"""WC_INSUFFICIENT unit tests (ADR-0024)."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.rules.financial.wc_insufficient import wc_insufficient
from domain.value_objects.balance_snapshot import BalanceSnapshot
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


def _annual(
    *,
    year: int = 2025,
    current_assets: int | None = None,
    current_liabilities: int | None = None,
) -> FinancialReport:
    balance_end = (
        BalanceSnapshot(
            current_assets=(
                Money(Decimal(current_assets), UZS) if current_assets is not None else None
            ),
            current_liabilities=(
                Money(Decimal(current_liabilities), UZS)
                if current_liabilities is not None
                else None
            ),
        )
        if current_assets is not None or current_liabilities is not None
        else None
    )
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=Money(Decimal(1_000_000_000), UZS),
        net_profit=Money(Decimal(100_000_000), UZS),
        balance_end=balance_end,
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
        as_of=date(2026, 5, 19),
        annual_reports=list(reports),
    )


class TestWcInsufficient:
    def test_fires_when_current_ratio_below_one(self) -> None:
        # CA=800M, CL=1B → ratio 0.8 < 1.0 → fires
        ev = wc_insufficient(
            _snapshot(_annual(current_assets=800_000_000, current_liabilities=1_000_000_000))
        )
        assert ev is not None
        assert Decimal(ev.evidence["current_ratio"]) < Decimal("1.0")
        assert Decimal(ev.evidence["working_capital"]) < Decimal(0)

    def test_silent_at_exactly_one(self) -> None:
        # CA=CL=1B → ratio 1.0 → boundary inclusive (>=1) silent
        assert (
            wc_insufficient(
                _snapshot(_annual(current_assets=1_000_000_000, current_liabilities=1_000_000_000))
            )
            is None
        )

    def test_silent_when_ratio_above_one(self) -> None:
        assert (
            wc_insufficient(
                _snapshot(_annual(current_assets=1_500_000_000, current_liabilities=1_000_000_000))
            )
            is None
        )

    def test_silent_when_balance_missing(self) -> None:
        assert wc_insufficient(_snapshot(_annual())) is None

    def test_silent_when_current_assets_missing(self) -> None:
        assert (
            wc_insufficient(_snapshot(_annual(current_liabilities=1_000_000_000)))
            is None
        )

    def test_silent_when_current_liabilities_missing(self) -> None:
        assert (
            wc_insufficient(_snapshot(_annual(current_assets=1_000_000_000)))
            is None
        )

    def test_silent_when_current_liabilities_zero(self) -> None:
        # CL=0 → деление на ноль защищено, формально WC бесконечен
        assert (
            wc_insufficient(
                _snapshot(_annual(current_assets=1_000_000_000, current_liabilities=0))
            )
            is None
        )

    def test_silent_when_no_annual_reports(self) -> None:
        assert wc_insufficient(_snapshot()) is None

    def test_uses_latest_annual(self) -> None:
        old = _annual(year=2024, current_assets=2_000_000_000, current_liabilities=1_000_000_000)
        new = _annual(year=2025, current_assets=500_000_000, current_liabilities=1_000_000_000)
        ev = wc_insufficient(_snapshot(old, new))
        assert ev is not None
        assert ev.evidence["year"] == "2025"
