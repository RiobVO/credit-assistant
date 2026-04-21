"""Тесты parse_header — извлечение шапки из xltx-форм.

После best-effort рефактора (CA-014 hardening): row/cell-level ошибки
становятся parse_warnings + None, не raise. Raise остаются только для
структурных ошибок (отсутствие list01, неподдерживаемый формат)."""

from datetime import date

import pytest

from domain.value_objects.inn import INN
from infrastructure.adapters.soliq_xltx.errors import UnsupportedFormatError
from infrastructure.adapters.soliq_xltx.format_detector import SoliqXltxFormat
from infrastructure.adapters.soliq_xltx.header_parser import parse_header
from tests.fixtures.soliq_xltx._factories import (
    build_form1_balance_sheet_wb,
    build_form2_income_statement_wb,
    build_profit_tax_wb,
    build_vat_declaration_wb,
)


class TestVatDeclarationHeader:
    def test_full_header_parsed(self) -> None:
        wb = build_vat_declaration_wb(
            inn=306399449,
            organization_name='"AZ RUHDIL SAVDO" MCHJ',
            period_year=2026,
            period_kind="месяц",
            submitted_at="20.04.2026",
        )
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.borrower_inn == INN("306399449")
        assert h.organization_name == '"AZ RUHDIL SAVDO" MCHJ'
        assert h.period_year == 2026
        assert h.period_kind == "month"
        assert h.period_index is None  # для VAT declaration номер не в шапке
        assert h.submitted_at == date(2026, 4, 20)
        assert h.parse_warnings == []

    def test_inn_as_string_with_whitespace(self) -> None:
        wb = build_vat_declaration_wb(inn="  306399449  ")
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.borrower_inn == INN("306399449")

    def test_quarter_kind(self) -> None:
        wb = build_vat_declaration_wb(period_kind="квартал")
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.period_kind == "quarter"

    def test_invalid_inn_warns_and_returns_none(self) -> None:
        wb = build_vat_declaration_wb(inn=12345)  # короче 9 цифр
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.borrower_inn is None
        assert any("INN" in w and "D3" in w for w in h.parse_warnings)
        # Остальные поля парсятся как обычно
        assert h.period_year == 2026

    def test_missing_org_name_warns_and_returns_none(self) -> None:
        wb = build_vat_declaration_wb()
        wb["list01"]["H9"].value = None
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.organization_name is None
        assert any("H9" in w for w in h.parse_warnings)

    def test_missing_year_warns_and_returns_none(self) -> None:
        wb = build_vat_declaration_wb()
        wb["list01"]["O5"].value = None
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.period_year is None
        assert any("O5" in w for w in h.parse_warnings)

    def test_missing_submitted_at_is_silent_none(self) -> None:
        # submitted_at и так был optional — не warning, просто None.
        wb = build_vat_declaration_wb()
        wb["list01"]["H17"].value = None
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.submitted_at is None
        assert h.parse_warnings == []

    def test_multiple_invalid_fields_collect_all_warnings(self) -> None:
        wb = build_vat_declaration_wb(inn=12345)
        wb["list01"]["H9"].value = None
        wb["list01"]["O5"].value = None
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.borrower_inn is None
        assert h.organization_name is None
        assert h.period_year is None
        assert len(h.parse_warnings) >= 3

    def test_empty_list01_returns_all_none_with_warnings(self) -> None:
        wb = build_vat_declaration_wb()
        for row in wb["list01"].iter_rows(min_row=1, max_row=20, max_col=20):
            for cell in row:
                cell.value = None
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.borrower_inn is None
        assert h.organization_name is None
        assert h.period_year is None
        assert h.parse_warnings  # не пустой


class TestForm2Header:
    def test_full_header(self) -> None:
        wb = build_form2_income_statement_wb(inn=306399449, period_year=2025, period_quarter=4)
        h = parse_header(wb, SoliqXltxFormat.FORM_2_INCOME_STATEMENT)
        assert h.borrower_inn == INN("306399449")
        assert h.period_year == 2025
        assert h.period_kind == "quarter"
        assert h.period_index == 4
        assert h.parse_warnings == []


class TestForm1Header:
    def test_full_header(self) -> None:
        wb = build_form1_balance_sheet_wb(inn=306399449, period_year=2025, period_quarter=4)
        h = parse_header(wb, SoliqXltxFormat.FORM_1_BALANCE_SHEET)
        assert h.borrower_inn == INN("306399449")
        assert h.period_year == 2025
        assert h.period_index == 4


class TestProfitTaxHeader:
    def test_full_header(self) -> None:
        wb = build_profit_tax_wb(inn=306399449, period_year=2026, period_quarter=1)
        h = parse_header(wb, SoliqXltxFormat.PROFIT_TAX)
        assert h.borrower_inn == INN("306399449")
        assert h.period_year == 2026
        assert h.period_index == 1


class TestUnsupported:
    """Структурные ошибки остаются raise — best-effort только на cell-уровне."""

    def test_registry_format_not_supported(self) -> None:
        wb = build_vat_declaration_wb()  # любой workbook
        with pytest.raises(UnsupportedFormatError):
            parse_header(wb, SoliqXltxFormat.VAT_REGISTRY_ILOVA)

    def test_unknown_format_not_supported(self) -> None:
        wb = build_vat_declaration_wb()
        with pytest.raises(UnsupportedFormatError):
            parse_header(wb, SoliqXltxFormat.UNKNOWN)
