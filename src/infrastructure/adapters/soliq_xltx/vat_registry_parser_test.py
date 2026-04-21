"""Тесты parse_vat_registry — парсинг ilova-реестра ЭСФ."""

from datetime import date
from decimal import Decimal

import pytest

from domain.value_objects.money import Currency, Money
from infrastructure.adapters.soliq_xltx.errors import UnsupportedFormatError
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
    """Structural ошибки (не тот формат) по-прежнему пробрасываются."""

    def test_wrong_format_raises_unsupported(self) -> None:
        wb = build_vat_declaration_wb()
        with pytest.raises(UnsupportedFormatError):
            parse_vat_registry(wb)


class TestTolerantParsing:
    """CA-014: row-level ошибки → skip + warn, не падение всего парсинга."""

    def test_garbage_seq_no_kept_with_zero(self) -> None:
        # seq_no — не critical поле (это №п/п). Bad value → 0, row парсится дальше.
        wb = build_vat_registry_wb(sales=[("A", "200000000", "1", "01.03.2026", 100.0, 12.0)])
        wb["list02"].cell(row=15, column=2).value = "не число"
        data = parse_vat_registry(wb)
        assert len(data.sales) == 1
        assert data.sales[0].seq_no == 0
        assert data.sales[0].counterparty_name == "A"
        assert data.skipped_rows_count == 0

    def test_invalid_date_format_skipped(self) -> None:
        wb = build_vat_registry_wb(
            sales=[("A", "200000000", "1", "2026-03-01", 100.0, 12.0)]  # ISO, не DD.MM.YYYY
        )
        data = parse_vat_registry(wb)
        assert data.sales == []
        assert data.skipped_rows_count == 1

    def test_missing_required_name_skipped(self) -> None:
        wb = build_vat_registry_wb(sales=[("A", "200000000", "1", "01.03.2026", 100.0, 12.0)])
        wb["list02"].cell(row=15, column=3).value = None
        data = parse_vat_registry(wb)
        assert data.sales == []
        assert data.skipped_rows_count == 1

    def test_partial_success_with_garbage_rows(self) -> None:
        # 5 валидных продаж + затираем 2-ю и 4-ю → 3 валидных, 2 skipped, totals по valid only.
        wb = build_vat_registry_wb(
            sales=[
                ("A", "200000000", "1", "01.03.2026", 1000.0, 120.0),
                ("B", "200000001", "2", "02.03.2026", 2000.0, 240.0),
                ("C", "200000002", "3", "03.03.2026", 3000.0, 360.0),
                ("D", "200000003", "4", "04.03.2026", 4000.0, 480.0),
                ("E", "200000004", "5", "05.03.2026", 5000.0, 600.0),
            ]
        )
        wb["list02"].cell(row=16, column=6).value = "garbage-date"  # 2-я строка — bad date
        wb["list02"].cell(row=18, column=3).value = None  # 4-я строка — пустое имя
        data = parse_vat_registry(wb)
        assert len(data.sales) == 3
        assert [r.invoice_no for r in data.sales] == ["1", "3", "5"]
        assert data.sales_vat_total == _uzs("1080")  # 120 + 360 + 600
        assert data.skipped_rows_count == 2

    def test_skipped_in_both_sales_and_purchases(self) -> None:
        wb = build_vat_registry_wb(
            sales=[("A", "200000000", "1", "01.03.2026", 1000.0, 120.0)],
            purchases=[("X", "200000099", "9", "09.03.2026", 9000.0, 1080.0)],
        )
        wb["list01"].cell(row=15, column=3).value = None  # испортить purchase (name)
        wb["list02"].cell(row=15, column=3).value = None  # испортить sale (name)
        data = parse_vat_registry(wb)
        assert data.sales == []
        assert data.purchases == []
        assert data.skipped_rows_count == 2
        assert len(data.parse_warnings) == 2

    def test_empty_registry_has_zero_skipped(self) -> None:
        wb = build_vat_registry_wb()
        data = parse_vat_registry(wb)
        assert data.skipped_rows_count == 0
        assert data.parse_warnings == []

    def test_skip_logged_with_structured_context(self, caplog: pytest.LogCaptureFixture) -> None:
        # Проверяем что про каждую пропущенную строку идёт WARNING с (sheet, row, reason).
        import logging

        wb = build_vat_registry_wb(sales=[("A", "200000000", "1", "01.03.2026", 100.0, 12.0)])
        wb["list02"].cell(row=15, column=6).value = "broken-date"
        with caplog.at_level(logging.WARNING):
            data = parse_vat_registry(wb)
        assert any("xltx.registry_row_skipped" in r.getMessage() for r in caplog.records)
        # И сам warning виден в DTO для UI
        assert any("list02" in w and "15" in w for w in data.parse_warnings)

    def test_warnings_include_row_and_reason(self) -> None:
        wb = build_vat_registry_wb(
            sales=[
                ("A", "200000000", "1", "01.03.2026", 1000.0, 120.0),
                ("B", "200000001", "2", "02.03.2026", 2000.0, 240.0),
            ]
        )
        wb["list02"].cell(row=16, column=6).value = "garbage-date"
        data = parse_vat_registry(wb)
        assert data.skipped_rows_count == 1
        assert len(data.parse_warnings) == 1
        msg = data.parse_warnings[0]
        assert "list02" in msg
        assert "16" in msg

    def test_optional_inn_empty_keeps_row(self) -> None:
        # Пустой ИНН (ПИНФЛ-розница) уже корректно поддерживался — не ломаем.
        wb = build_vat_registry_wb(
            sales=[("ABDURAXMONOVA NARGIZA", None, "1461", "29.03.2026", 464285.71, 55714.29)]
        )
        data = parse_vat_registry(wb)
        assert len(data.sales) == 1
        assert data.sales[0].counterparty_inn is None
        assert data.parse_warnings == []
