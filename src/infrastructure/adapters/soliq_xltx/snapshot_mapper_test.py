"""Маппер xltx → SoliqChunk: один VAT-период из пары (декларация, реестр)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money
from infrastructure.adapters.soliq_xltx.header_parser import SoliqXltxHeader
from infrastructure.adapters.soliq_xltx.snapshot_mapper import (
    XltxBorrowerMismatchError,
    to_soliq_chunk,
)
from infrastructure.adapters.soliq_xltx.vat_declaration_parser import VatDeclarationData
from infrastructure.adapters.soliq_xltx.vat_registry_parser import VatRegistryData

UZS = Currency.UZS
INN_OK = INN("306399449")


def _money(amount: str | int) -> Money:
    return Money(Decimal(amount), UZS)


def _header(
    *,
    inn: INN = INN_OK,
    year: int = 2026,
    submitted_at: date | None = date(2026, 4, 25),
) -> SoliqXltxHeader:
    return SoliqXltxHeader(
        borrower_inn=inn,
        organization_name="ООО Тест",
        period_year=year,
        period_kind="month",
        period_index=None,
        submitted_at=submitted_at,
    )


def _declaration(
    *,
    inn: INN = INN_OK,
    year: int = 2026,
    vat_charged: int | None = 62_799_985,
    submitted_at: date | None = date(2026, 4, 25),
) -> VatDeclarationData:
    return VatDeclarationData(
        header=_header(inn=inn, year=year, submitted_at=submitted_at),
        sales_total_excl_vat=_money(523_333_213),
        vat_charged_total=_money(vat_charged) if vat_charged is not None else None,
        sales_via_esf=None,
        vat_via_esf=None,
        sales_via_kkm=None,
        vat_via_kkm=None,
        sales_via_export=None,
        vat_via_export=None,
        sales_via_marketplace=None,
        vat_via_marketplace=None,
        sales_via_other=None,
        vat_via_other=None,
        vat_to_offset_year_cumulative=None,
        vat_to_offset_total=None,
    )


def _registry(*, sales_vat_total: int = 63_550_200) -> VatRegistryData:
    return VatRegistryData(
        sales=[],
        purchases=[],
        sales_vat_total=_money(sales_vat_total),
        purchases_vat_total=_money(0),
        sales_amount_total=_money(0),
        purchases_amount_total=_money(0),
    )


class TestPeriodRange:
    def test_march_31_days(self) -> None:
        chunk = to_soliq_chunk(
            declaration=_declaration(year=2026),
            registry=_registry(),
            borrower_inn=INN_OK,
            period_month=3,
        )
        assert len(chunk.vat_periods) == 1
        assert chunk.vat_periods[0].period == DateRange(
            date(2026, 3, 1), date(2026, 3, 31)
        )

    def test_february_non_leap(self) -> None:
        chunk = to_soliq_chunk(
            declaration=_declaration(year=2026),
            registry=_registry(),
            borrower_inn=INN_OK,
            period_month=2,
        )
        assert chunk.vat_periods[0].period == DateRange(
            date(2026, 2, 1), date(2026, 2, 28)
        )

    def test_february_leap_year(self) -> None:
        chunk = to_soliq_chunk(
            declaration=_declaration(year=2024),
            registry=_registry(),
            borrower_inn=INN_OK,
            period_month=2,
        )
        assert chunk.vat_periods[0].period == DateRange(
            date(2024, 2, 1), date(2024, 2, 29)
        )


class TestVatPeriodFields:
    def test_propagates_real_data_amounts(self) -> None:
        # Реальные числа из smoke папы (март 2026).
        chunk = to_soliq_chunk(
            declaration=_declaration(vat_charged=62_799_985),
            registry=_registry(sales_vat_total=63_550_200),
            borrower_inn=INN_OK,
            period_month=3,
        )
        period = chunk.vat_periods[0]
        assert period.vat_declared is not None
        assert period.vat_declared.amount == Decimal(62_799_985)
        assert period.esf_seller_vat_total is not None
        assert period.esf_seller_vat_total.amount == Decimal(63_550_200)

    def test_passes_submitted_at_through(self) -> None:
        chunk = to_soliq_chunk(
            declaration=_declaration(submitted_at=date(2026, 4, 20)),
            registry=_registry(),
            borrower_inn=INN_OK,
            period_month=3,
        )
        assert chunk.vat_periods[0].submitted_at == date(2026, 4, 20)

    def test_vat_declared_none_when_declaration_total_missing(self) -> None:
        # Декларация без vat_charged_total — ситуация пустой декларации; правило
        # потом просто молчит, но маппер должен пропустить None без ошибки.
        chunk = to_soliq_chunk(
            declaration=_declaration(vat_charged=None),
            registry=_registry(),
            borrower_inn=INN_OK,
            period_month=3,
        )
        assert chunk.vat_periods[0].vat_declared is None


class TestBorrowerInn:
    def test_chunk_carries_borrower_inn(self) -> None:
        chunk = to_soliq_chunk(
            declaration=_declaration(),
            registry=_registry(),
            borrower_inn=INN_OK,
            period_month=3,
        )
        assert chunk.borrower_inn == INN_OK

    def test_mismatch_raises(self) -> None:
        other = INN("123456789")
        with pytest.raises(XltxBorrowerMismatchError) as exc:
            to_soliq_chunk(
                declaration=_declaration(inn=other),
                registry=_registry(),
                borrower_inn=INN_OK,
                period_month=3,
            )
        assert exc.value.expected == INN_OK
        assert exc.value.actual == other


class TestPeriodMonthValidation:
    @pytest.mark.parametrize("month", [0, 13, -1, 99])
    def test_out_of_range_rejected(self, month: int) -> None:
        with pytest.raises(ValueError, match=r"period_month must be in 1\.\.12"):
            to_soliq_chunk(
                declaration=_declaration(),
                registry=_registry(),
                borrower_inn=INN_OK,
                period_month=month,
            )
