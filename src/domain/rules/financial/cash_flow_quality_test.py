"""Тесты CASH_FLOW_QUALITY (ADR-0024 Session 2)."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.rules.financial.cash_flow_quality import cash_flow_quality
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
    net_profit: int = 500_000_000,
    operating_cash_flow: int | None = None,
) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=_money(5_000_000_000),
        net_profit=_money(net_profit),
        operating_cash_flow=(
            _money(operating_cash_flow) if operating_cash_flow is not None else None
        ),
    )


def _snapshot(reports: list[FinancialReport]) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 8),
        annual_reports=reports,
    )


class TestCashFlowQuality:
    """Fires/silent/edge cases для OCF/NP < 0.50 threshold."""

    def test_fires_when_ocf_below_half_net_profit(self) -> None:
        """OCF=200M, NP=500M → ratio=0.40 < 0.50, fires."""
        report = _annual(net_profit=500_000_000, operating_cash_flow=200_000_000)
        result = cash_flow_quality(_snapshot([report]))
        assert result is not None
        assert result.evidence["ocf_to_net_profit"] == "0.40"
        assert result.evidence["operating_cash_flow"] == "200000000"
        assert result.evidence["net_profit"] == "500000000"

    def test_fires_when_ocf_negative_but_np_positive(self) -> None:
        """OCF=-100M (отток), NP=500M → ratio=-0.20 < 0.50, fires."""
        report = _annual(net_profit=500_000_000, operating_cash_flow=-100_000_000)
        result = cash_flow_quality(_snapshot([report]))
        assert result is not None
        assert "-0,20" in result.message

    def test_silent_when_ratio_at_boundary_50_pct(self) -> None:
        """OCF=250M, NP=500M → ratio=0.50 (точно граница) → silent (≥0.50)."""
        report = _annual(net_profit=500_000_000, operating_cash_flow=250_000_000)
        result = cash_flow_quality(_snapshot([report]))
        assert result is None

    def test_silent_when_ratio_above_50_pct(self) -> None:
        """OCF=400M, NP=500M → ratio=0.80 ≥ 0.50, silent."""
        report = _annual(net_profit=500_000_000, operating_cash_flow=400_000_000)
        result = cash_flow_quality(_snapshot([report]))
        assert result is None

    def test_silent_when_ocf_missing(self) -> None:
        """OCF None → silent (нет данных, не сигнал)."""
        report = _annual(net_profit=500_000_000, operating_cash_flow=None)
        result = cash_flow_quality(_snapshot([report]))
        assert result is None

    def test_silent_when_net_profit_zero(self) -> None:
        """NP=0 → silent (ratio не имеет смысла; ловит NEGATIVE_PROFIT_3Q)."""
        report = _annual(net_profit=0, operating_cash_flow=200_000_000)
        result = cash_flow_quality(_snapshot([report]))
        assert result is None

    def test_silent_when_net_profit_negative(self) -> None:
        """NP < 0 → silent (та же причина — этот срез про прибыль, не убыток)."""
        report = _annual(net_profit=-100_000_000, operating_cash_flow=200_000_000)
        result = cash_flow_quality(_snapshot([report]))
        assert result is None

    def test_silent_when_annual_reports_empty(self) -> None:
        result = cash_flow_quality(_snapshot([]))
        assert result is None

    def test_uses_latest_annual_report(self) -> None:
        """Если несколько annual reports — берёт latest по period.end."""
        old = _annual(year=2024, net_profit=500_000_000, operating_cash_flow=100_000_000)
        new = _annual(year=2025, net_profit=500_000_000, operating_cash_flow=400_000_000)
        # 2024 (OCF/NP=0.20) fires, 2025 (0.80) silent — должно взять 2025.
        result = cash_flow_quality(_snapshot([old, new]))
        assert result is None
