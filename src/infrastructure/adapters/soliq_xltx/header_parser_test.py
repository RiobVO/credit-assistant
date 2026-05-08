"""Тесты parse_header — извлечение шапки из xltx-форм."""

from datetime import date

import pytest

from domain.value_objects.inn import INN
from infrastructure.adapters.soliq_xltx.errors import (
    MalformedXltxError,
    UnsupportedFormatError,
)
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

    def test_inn_as_string_with_whitespace(self) -> None:
        wb = build_vat_declaration_wb(inn="  306399449  ")
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.borrower_inn == INN("306399449")

    def test_quarter_kind(self) -> None:
        wb = build_vat_declaration_wb(period_kind="квартал")
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.period_kind == "quarter"

    def test_invalid_inn_raises_malformed_with_location(self) -> None:
        wb = build_vat_declaration_wb(inn=12345)  # короче 9 цифр
        with pytest.raises(MalformedXltxError) as exc:
            parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert exc.value.sheet == "list01"
        assert exc.value.coord == "D3"
        assert "invalid INN" in str(exc.value)

    def test_missing_org_name_raises(self) -> None:
        wb = build_vat_declaration_wb()
        wb["list01"]["H9"].value = None
        with pytest.raises(MalformedXltxError) as exc:
            parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert exc.value.coord == "H9"

    def test_missing_year_raises(self) -> None:
        wb = build_vat_declaration_wb()
        wb["list01"]["O5"].value = None
        with pytest.raises(MalformedXltxError) as exc:
            parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert exc.value.coord == "O5"

    def test_missing_submitted_at_is_none_not_error(self) -> None:
        wb = build_vat_declaration_wb()
        wb["list01"]["H17"].value = None
        h = parse_header(wb, SoliqXltxFormat.VAT_DECLARATION)
        assert h.submitted_at is None


class TestForm2Header:
    def test_full_header(self) -> None:
        wb = build_form2_income_statement_wb(inn=306399449, period_year=2025, period_quarter=4)
        h = parse_header(wb, SoliqXltxFormat.FORM_2_INCOME_STATEMENT)
        assert h.borrower_inn == INN("306399449")
        assert h.period_year == 2025
        assert h.period_kind == "quarter"
        assert h.period_index == 4


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
    def test_registry_format_not_supported(self) -> None:
        wb = build_vat_declaration_wb()  # любой workbook
        with pytest.raises(UnsupportedFormatError):
            parse_header(wb, SoliqXltxFormat.VAT_REGISTRY_ILOVA)

    def test_unknown_format_not_supported(self) -> None:
        wb = build_vat_declaration_wb()
        with pytest.raises(UnsupportedFormatError):
            parse_header(wb, SoliqXltxFormat.UNKNOWN)
