"""Тесты OFF_BALANCE_COMMITMENTS (ADR-0024 Session 2)."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.rules.financial.off_balance_commitments import off_balance_commitments
from domain.value_objects.balance_snapshot import BalanceSnapshot
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


def _money(amount: int) -> Money:
    return Money(Decimal(amount), UZS)


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("123456789"),
        name='ООО "Тест"',
        legal_form=LegalForm.LLC,
        registration_date=date(2020, 1, 1),
        director_name="Иванов",
        director_appointed_at=date(2022, 1, 1),
        oked_main="62.01",
        registered_address="Ташкент, ул. Тестовая, 1",
    )


def _annual(
    *,
    year: int = 2025,
    assets: int | None = 1_000_000_000,
    guarantees: int | None = None,
    leases: int | None = None,
    letters_of_credit: int | None = None,
) -> FinancialReport:
    balance_end = (
        BalanceSnapshot(assets=_money(assets)) if assets is not None else None
    )
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=_money(5_000_000_000),
        net_profit=_money(500_000_000),
        guarantees_outstanding=_money(guarantees) if guarantees is not None else None,
        leases_outstanding=_money(leases) if leases is not None else None,
        letters_of_credit_outstanding=(
            _money(letters_of_credit) if letters_of_credit is not None else None
        ),
        balance_end=balance_end,
    )


def _snapshot(reports: list[FinancialReport]) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 8),
        annual_reports=reports,
    )


class TestOffBalanceCommitments:
    """3 unit-теста: fires (>0.50) / silent (≤0.50) / silent (no data)."""

    def test_fires_when_total_off_balance_exceeds_50_pct(self) -> None:
        """600M гарантий + 0 lease + 0 LoC = 600M против 1B активов = 60%, fires."""
        report = _annual(assets=1_000_000_000, guarantees=600_000_000)
        result = off_balance_commitments(_snapshot([report]))
        assert result is not None
        assert result.evidence["ratio_pct"] == "60.0"
        assert result.evidence["off_balance_total"] == "600000000"
        assert result.evidence["total_assets"] == "1000000000"

    def test_fires_with_combined_three_fields(self) -> None:
        """300M+150M+100M = 550M против 1B = 55%, fires."""
        report = _annual(
            assets=1_000_000_000,
            guarantees=300_000_000,
            leases=150_000_000,
            letters_of_credit=100_000_000,
        )
        result = off_balance_commitments(_snapshot([report]))
        assert result is not None
        assert result.evidence["off_balance_total"] == "550000000"

    def test_silent_when_ratio_at_boundary_50_pct(self) -> None:
        """ratio = 0.50 (точно граница) → silent. Threshold strict >0.50."""
        report = _annual(assets=1_000_000_000, guarantees=500_000_000)
        result = off_balance_commitments(_snapshot([report]))
        assert result is None

    def test_silent_when_ratio_below_50_pct(self) -> None:
        """40% < 50% → silent."""
        report = _annual(assets=1_000_000_000, guarantees=400_000_000)
        result = off_balance_commitments(_snapshot([report]))
        assert result is None

    def test_silent_when_all_three_fields_none(self) -> None:
        """Все 3 off-balance None → silent (нет данных, не сигнал)."""
        report = _annual(assets=1_000_000_000)
        result = off_balance_commitments(_snapshot([report]))
        assert result is None

    def test_silent_when_total_assets_missing(self) -> None:
        """balance_end.assets None → None (нет знаменателя)."""
        report = _annual(assets=None, guarantees=600_000_000)
        result = off_balance_commitments(_snapshot([report]))
        assert result is None

    def test_silent_when_total_assets_zero(self) -> None:
        """total_assets ≤ 0 → None (деление на ≤0)."""
        report = _annual(assets=0, guarantees=600_000_000)
        # _money(0) даёт assets с amount=0 — balance_end не пустой
        result = off_balance_commitments(_snapshot([report]))
        assert result is None

    def test_silent_when_annual_reports_empty(self) -> None:
        result = off_balance_commitments(_snapshot([]))
        assert result is None

    def test_partial_data_one_field_only(self) -> None:
        """Только leases заполнено, остальные None → считаем как «None=0»;
        51% > 50% → fires. Banker должен видеть сигнал даже при partial data."""
        report = _annual(assets=1_000_000_000, leases=510_000_000)
        result = off_balance_commitments(_snapshot([report]))
        assert result is not None
        assert result.evidence["off_balance_total"] == "510000000"
        assert result.evidence["guarantees_outstanding"] == "null"
        assert result.evidence["letters_of_credit_outstanding"] == "null"
