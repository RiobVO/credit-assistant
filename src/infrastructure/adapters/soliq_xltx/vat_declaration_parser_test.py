"""Тесты parse_vat_declaration."""

from decimal import Decimal

import pytest
from openpyxl import Workbook

from domain.value_objects.money import Currency, Money
from infrastructure.adapters.soliq_xltx.errors import (
    MalformedXltxError,
    UnsupportedFormatError,
)
from infrastructure.adapters.soliq_xltx.vat_declaration_parser import (
    parse_vat_declaration,
)
from tests.fixtures.soliq_xltx._factories import (
    build_form2_income_statement_wb,
    build_vat_declaration_wb,
)


def _uzs(s: str) -> Money:
    return Money(Decimal(s), Currency.UZS)


class TestHappyPath:
    def test_full_paper_real_numbers(self) -> None:
        # Цифры из реального файла папы (март 2026):
        wb = build_vat_declaration_wb(
            sales_total_excl_vat=523333214.06,
            sales_total_vat=62799985.69,
            sales_via_esf=(523333214.06, 62799985.94),
            sales_via_kkm=(0.0, 0.0),
            sales_via_export=(0.0, "x"),
            sales_via_marketplace=(0.0, 0.0),
            sales_via_other=(None, 0.0),
            vat_to_offset_year_cumulative=(1416681390.98, 169838602.88),
            vat_to_offset_total=167588345.73,
        )
        data = parse_vat_declaration(wb)
        assert data.header.borrower_inn.value == "306399449"
        assert data.sales_total_excl_vat == _uzs("523333214.06")
        assert data.vat_charged_total == _uzs("62799985.69")
        assert data.sales_via_esf == _uzs("523333214.06")
        assert data.vat_via_esf == _uzs("62799985.94")
        # Экспорт: НДС 'x' → None (не applicable)
        assert data.sales_via_export == _uzs("0")
        assert data.vat_via_export is None
        # Прочие: стоимость не указана → None, НДС 0
        assert data.sales_via_other is None
        assert data.vat_via_other == _uzs("0")
        assert data.vat_to_offset_total == _uzs("167588345.73")

    def test_decimal_precision_preserved(self) -> None:
        wb = build_vat_declaration_wb(sales_total_vat=62799985.69)
        data = parse_vat_declaration(wb)
        assert data.vat_charged_total is not None
        # Decimal → str → Decimal сохраняет 2 знака без рассинхрона binary float
        assert str(data.vat_charged_total.amount) == "62799985.69"

    def test_x_marker_lowercase_latin(self) -> None:
        wb = build_vat_declaration_wb(sales_via_export=(0.0, "x"))
        data = parse_vat_declaration(wb)
        assert data.vat_via_export is None

    def test_x_marker_uppercase_cyrillic(self) -> None:
        wb = build_vat_declaration_wb(sales_via_export=(0.0, "Х"))
        data = parse_vat_declaration(wb)
        assert data.vat_via_export is None

    def test_string_money_with_comma_separator(self) -> None:
        # На случай если cells приходят строками "62799985,69"
        wb = build_vat_declaration_wb()
        wb["list02"]["G6"].value = "62 799 985,69"
        # пробелы в числах не разбираем — это уже искажение формата → ошибка
        with pytest.raises(MalformedXltxError):
            parse_vat_declaration(wb)


class TestEdgeCases:
    def test_vat_charged_zero_when_no_sales(self) -> None:
        wb = build_vat_declaration_wb(
            sales_total_excl_vat=0.0,
            sales_total_vat=0.0,
            sales_via_esf=(0.0, 0.0),
        )
        data = parse_vat_declaration(wb)
        assert data.vat_charged_total == _uzs("0")
        assert data.sales_via_esf == _uzs("0")

    def test_only_esf_channel_others_zero(self) -> None:
        # Реальный кейс папы — продажи только через ЭСФ
        wb = build_vat_declaration_wb(
            sales_via_kkm=(0.0, 0.0),
            sales_via_export=(0.0, "x"),
            sales_via_marketplace=(0.0, 0.0),
        )
        data = parse_vat_declaration(wb)
        assert data.sales_via_kkm == _uzs("0")
        assert data.sales_via_marketplace == _uzs("0")


class TestErrors:
    def test_wrong_format_raises_unsupported(self) -> None:
        wb = build_form2_income_statement_wb()
        with pytest.raises(UnsupportedFormatError):
            parse_vat_declaration(wb)

    def test_unknown_format_raises_unsupported(self) -> None:
        wb = Workbook()  # пустой, нет list01
        with pytest.raises(UnsupportedFormatError):
            parse_vat_declaration(wb)

    def test_missing_list02_raises_unsupported(self) -> None:
        wb = build_vat_declaration_wb()
        del wb["list02"]
        with pytest.raises(UnsupportedFormatError, match="list02"):
            parse_vat_declaration(wb)

    def test_missing_list04_raises_unsupported(self) -> None:
        wb = build_vat_declaration_wb()
        del wb["list04"]
        with pytest.raises(UnsupportedFormatError, match="list04"):
            parse_vat_declaration(wb)

    def test_garbage_money_cell_raises_malformed(self) -> None:
        wb = build_vat_declaration_wb()
        wb["list02"]["G6"].value = "abc-not-a-number"
        with pytest.raises(MalformedXltxError) as exc:
            parse_vat_declaration(wb)
        assert exc.value.sheet == "list02"
        assert exc.value.coord == "G6"
