"""Тесты parse_vat_registry — парсинг ilova-реестра ЭСФ."""

from datetime import date
from decimal import Decimal

import pytest

from domain.value_objects.money import Currency, Money
from infrastructure.adapters.soliq_xltx.errors import (
    MalformedXltxError,
    UnsupportedFormatError,
)
from infrastructure.adapters.soliq_xltx.vat_registry_parser import parse_vat_registry
from tests.fixtures.soliq_xltx._factories import (
    build_vat_declaration_wb,
    build_vat_registry_wb,
)


def _uzs(s: str) -> Money:
    return Money(Decimal(s), Currency.UZS)


class TestSalesParsing:
    def test_parses_multiple_sales_rows(self) -> None:
        wb = build_vat_registry_wb(
            sales=[
                ('"BUYER A" MCHJ', "310413864", "1034", "02.03.2026", 1181250.0, 141750.0),
                ('"BUYER B" MCHJ', "308332689", "1116", "06.03.2026", 2989285.71, 358714.29),
                ('"BUYER C" XK', "300546790", "1185", "10.03.2026", 267857.14, 32142.86),
            ]
        )
        data = parse_vat_registry(wb)
        assert len(data.sales) == 3
        assert data.sales[0].counterparty_name == '"BUYER A" MCHJ'
        assert data.sales[0].counterparty_inn == "310413864"
        assert data.sales[0].invoice_no == "1034"
        assert data.sales[0].invoice_date == date(2026, 3, 2)
        assert data.sales[0].amount_excl_vat == _uzs("1181250")
        assert data.sales[0].vat_amount == _uzs("141750")

    def test_pinfl_buyer_inn_is_none(self) -> None:
        # Розничные физлица — ИНН пуст (есть только ПИНФЛ, который не приходит в реестр)
        wb = build_vat_registry_wb(
            sales=[
                ("ABDURAXMONOVA NARGIZA", None, "1461", "29.03.2026", 464285.71, 55714.29),
            ]
        )
        data = parse_vat_registry(wb)
        assert data.sales[0].counterparty_inn is None

    def test_decimal_precision_preserved_in_amounts(self) -> None:
        wb = build_vat_registry_wb(
            sales=[
                ("X", "200000000", "Z", "01.03.2026", 2989285.71, 358714.29),
            ]
        )
        data = parse_vat_registry(wb)
        # Float 2989285.71 → str → Decimal должен сохранить 2 знака
        assert str(data.sales[0].amount_excl_vat.amount) == "2989285.71"


class TestPurchasesParsing:
    def test_parses_purchases(self) -> None:
        wb = build_vat_registry_wb(
            purchases=[
                ('"SUPPLIER X" MCHJ', "310122000", "1", "02.03.2026", 27321428.54, 3278571.42),
                ('"SUPPLIER Y" MCHJ', "301336711", "440", "04.03.2026", 28285714.29, 3394285.71),
            ]
        )
        data = parse_vat_registry(wb)
        assert len(data.purchases) == 2
        assert data.sales == []  # sales не передавали


class TestTotals:
    def test_sales_vat_total_equals_sum(self) -> None:
        wb = build_vat_registry_wb(
            sales=[
                ("A", "200000000", "1", "01.03.2026", 1000.0, 120.0),
                ("B", "200000001", "2", "02.03.2026", 2000.0, 240.0),
                ("C", "200000002", "3", "03.03.2026", 3000.0, 360.0),
            ]
        )
        data = parse_vat_registry(wb)
        # Точная сумма без ошибок binary float (Decimal-based addition)
        assert data.sales_vat_total == _uzs("720")
        assert data.sales_amount_total == _uzs("6000")

    def test_purchases_vat_total_equals_sum(self) -> None:
        wb = build_vat_registry_wb(
            purchases=[
                ("A", "200000000", "1", "01.03.2026", 100.50, 12.06),
                ("B", "200000001", "2", "02.03.2026", 200.50, 24.06),
            ]
        )
        data = parse_vat_registry(wb)
        assert str(data.purchases_vat_total.amount) == "36.12"

    def test_empty_registry_has_zero_totals(self) -> None:
        wb = build_vat_registry_wb()
        data = parse_vat_registry(wb)
        assert data.sales == []
        assert data.purchases == []
        assert data.sales_vat_total == _uzs("0")
        assert data.purchases_vat_total == _uzs("0")


class TestErrors:
    def test_wrong_format_raises_unsupported(self) -> None:
        wb = build_vat_declaration_wb()
        with pytest.raises(UnsupportedFormatError):
            parse_vat_registry(wb)

    def test_garbage_seq_no_raises_malformed(self) -> None:
        wb = build_vat_registry_wb(sales=[("A", "200000000", "1", "01.03.2026", 100.0, 12.0)])
        wb["list02"].cell(row=15, column=2).value = "не число"
        with pytest.raises(MalformedXltxError) as exc:
            parse_vat_registry(wb)
        assert exc.value.row_no == 15

    def test_invalid_date_format_raises_malformed(self) -> None:
        wb = build_vat_registry_wb(
            sales=[("A", "200000000", "1", "2026-03-01", 100.0, 12.0)]  # ISO, не DD.MM.YYYY
        )
        with pytest.raises(MalformedXltxError) as exc:
            parse_vat_registry(wb)
        assert exc.value.row_no == 15
        assert "expected DD.MM.YYYY" in str(exc.value)

    def test_missing_required_name_raises_malformed(self) -> None:
        wb = build_vat_registry_wb(sales=[("A", "200000000", "1", "01.03.2026", 100.0, 12.0)])
        wb["list02"].cell(row=15, column=3).value = None
        with pytest.raises(MalformedXltxError) as exc:
            parse_vat_registry(wb)
        assert exc.value.row_no == 15
