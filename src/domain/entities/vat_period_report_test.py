"""VatPeriodReport: базовые инварианты."""

from datetime import date
from decimal import Decimal

import pytest

from domain.entities.vat_period_report import VatPeriodReport
from domain.value_objects.date_range import DateRange, InvalidDateRangeError
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS
PERIOD = DateRange(date(2026, 3, 1), date(2026, 3, 31))


class TestConstruction:
    def test_minimal_period_only(self) -> None:
        report = VatPeriodReport(period=PERIOD)
        assert report.period == PERIOD
        assert report.vat_declared is None
        assert report.esf_seller_vat_total is None
        assert report.submitted_at is None

    def test_full_fields(self) -> None:
        report = VatPeriodReport(
            period=PERIOD,
            vat_declared=Money(Decimal("62799985.69"), UZS),
            esf_seller_vat_total=Money(Decimal("63550200.23"), UZS),
            submitted_at=date(2026, 4, 25),
        )
        assert report.vat_declared is not None
        assert report.vat_declared.amount == Decimal("62799985.69")
        assert report.esf_seller_vat_total is not None
        assert report.submitted_at == date(2026, 4, 25)


class TestImmutability:
    def test_frozen_dataclass(self) -> None:
        report = VatPeriodReport(period=PERIOD)
        with pytest.raises(AttributeError):
            report.vat_declared = Money(Decimal(1), UZS)  # type: ignore[misc]


class TestPeriodInvariants:
    def test_invalid_period_rejected_at_date_range_level(self) -> None:
        with pytest.raises(InvalidDateRangeError):
            VatPeriodReport(period=DateRange(date(2026, 3, 31), date(2026, 3, 1)))


class TestEquality:
    def test_equal_when_all_fields_match(self) -> None:
        a = VatPeriodReport(
            period=PERIOD,
            vat_declared=Money(Decimal(100), UZS),
            esf_seller_vat_total=Money(Decimal(80), UZS),
        )
        b = VatPeriodReport(
            period=PERIOD,
            vat_declared=Money(Decimal(100), UZS),
            esf_seller_vat_total=Money(Decimal(80), UZS),
        )
        assert a == b
