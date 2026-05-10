"""Тесты parse_vat_declaration.

Best-effort семантика (CA-014 hardening): cell-level ошибки → warning + None.
Raise остаётся только для отсутствующих list02/list04 (структурный)."""

from decimal import Decimal

import pytest
from openpyxl import Workbook

from domain.value_objects.money import Currency, Money
from infrastructure.adapters.soliq_xltx.errors import UnsupportedFormatError
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
        assert data.header.borrower_inn is not None
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

    def test_string_money_with_spaces_warns_and_returns_none(self) -> None:
        # Пробелы в числах не разбираем — это искажение формата → warning + None.
        wb = build_vat_declaration_wb()
        wb["list02"]["G6"].value = "62 799 985,69"
        data = parse_vat_declaration(wb)
        assert data.vat_charged_total is None
        assert any("G6" in w for w in data.parse_warnings)
        # Остальные поля парсятся
        assert data.sales_via_esf is not None


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

    def test_garbage_money_cell_warns_and_returns_none(self) -> None:
        wb = build_vat_declaration_wb()
        wb["list02"]["G6"].value = "abc-not-a-number"
        data = parse_vat_declaration(wb)
        assert data.vat_charged_total is None
        assert any("G6" in w for w in data.parse_warnings)


class TestBestEffort:
    """CA-014: cell-level ошибки → warn + None, парсер продолжает работу."""

    def test_empty_content_returns_all_none_with_warnings(self) -> None:
        # Валидная структура (8 листов), но все cells пустые.
        wb = build_vat_declaration_wb()
        for sheet in (wb["list02"], wb["list04"]):
            for row in sheet.iter_rows(min_row=1, max_row=40, max_col=10):
                for cell in row:
                    cell.value = None
        data = parse_vat_declaration(wb)
        assert data.vat_charged_total is None
        assert data.sales_total_excl_vat is None
        # Header тоже посчитан best-effort
        assert isinstance(data.parse_warnings, list)

    def test_partial_garbage_cells_collect_warnings(self) -> None:
        wb = build_vat_declaration_wb()
        wb["list02"]["G6"].value = "garbage"
        wb["list02"]["F7"].value = "more-garbage"
        wb["list04"]["G37"].value = "junk"
        data = parse_vat_declaration(wb)
        assert data.vat_charged_total is None
        assert data.sales_via_esf is None
        assert data.vat_to_offset_total is None
        # Каждое поле даёт warning (как минимум 3)
        assert len(data.parse_warnings) >= 3
        # Хорошие cells всё равно парсятся
        assert data.sales_via_kkm is not None

    def test_header_warnings_propagate_into_declaration_warnings(self) -> None:
        wb = build_vat_declaration_wb(inn=12345)  # битый ИНН шапки
        data = parse_vat_declaration(wb)
        assert data.header.borrower_inn is None
        # parse_warnings агрегируют header + body
        assert any("D3" in w for w in data.parse_warnings)
