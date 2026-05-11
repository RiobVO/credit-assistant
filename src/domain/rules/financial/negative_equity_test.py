"""Тесты NEGATIVE_EQUITY (CA-049).

Контракт: срабатывает на latest annual report, если equity ≤ 0. Boundary
inclusive (equity = 0 fires). None equity (FORM_1 не загружен) — silent.
"""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.rules.financial.negative_equity import negative_equity
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


def _annual(year: int, *, equity: int | None) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=Money(Decimal(1_000_000_000), UZS),
        net_profit=Money(Decimal(100_000_000), UZS),
        taxes_paid=Money(Decimal(0), UZS),
        equity=Money(Decimal(equity), UZS) if equity is not None else None,
    )


def _snapshot(*reports: FinancialReport) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=Borrower(
            inn=INN("123456789"),
            name="ООО Тест",
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


class TestNegativeEquity:
    def test_fires_when_equity_negative(self) -> None:
        ev = negative_equity(_snapshot(_annual(2025, equity=-100_000_000)))
        assert ev is not None
        assert "Отрицательный" in ev.message

    def test_fires_when_equity_zero(self) -> None:
        """Boundary inclusive: equity = 0 → fires. Symmetric с NEGATIVE_PROFIT_3Q."""
        ev = negative_equity(_snapshot(_annual(2025, equity=0)))
        assert ev is not None

    def test_silent_when_equity_positive(self) -> None:
        assert negative_equity(_snapshot(_annual(2025, equity=100_000_000))) is None

    def test_silent_when_equity_field_missing(self) -> None:
        """equity=None (FORM_1 не загружен) ≠ equity=0. Без FORM_1 правило молчит."""
        assert negative_equity(_snapshot(_annual(2025, equity=None))) is None

    def test_silent_when_no_annual_reports(self) -> None:
        """Пустой annual_reports — нет данных для проверки."""
        s = BorrowerSnapshot(
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
        )
        assert negative_equity(s) is None

    def test_picks_latest_annual_report(self) -> None:
        """Три отчёта: 2023 negative, 2024 positive, 2025 negative — latest=2025 fires."""
        ev = negative_equity(
            _snapshot(
                _annual(2023, equity=-50_000_000),
                _annual(2024, equity=100_000_000),
                _annual(2025, equity=-200_000_000),
            )
        )
        assert ev is not None
        assert ev.evidence["year"] == "2025"

    def test_evidence_contains_rounded_equity_and_year(self) -> None:
        ev = negative_equity(_snapshot(_annual(2024, equity=-123_456_789)))
        assert ev is not None
        # CA-021: 2 знака после запятой даже когда значение целое.
        assert ev.evidence["equity"] == "-123456789.00"
        assert ev.evidence["year"] == "2024"
