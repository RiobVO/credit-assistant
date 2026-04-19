"""Тесты detect_format для всех 5 поддерживаемых форм + UNKNOWN-кейсы."""

from openpyxl import Workbook

from infrastructure.adapters.soliq_xltx.format_detector import (
    SoliqXltxFormat,
    detect_format,
)
from tests.fixtures.soliq_xltx._factories import (
    build_form1_balance_sheet_wb,
    build_form2_income_statement_wb,
    build_profit_tax_wb,
    build_vat_declaration_wb,
    build_vat_registry_wb,
)


def test_detect_vat_declaration() -> None:
    wb = build_vat_declaration_wb()
    assert detect_format(wb) == SoliqXltxFormat.VAT_DECLARATION


def test_detect_vat_registry_ilova() -> None:
    wb = build_vat_registry_wb()
    assert detect_format(wb) == SoliqXltxFormat.VAT_REGISTRY_ILOVA


def test_detect_form2_income_statement() -> None:
    wb = build_form2_income_statement_wb()
    assert detect_format(wb) == SoliqXltxFormat.FORM_2_INCOME_STATEMENT


def test_detect_form1_balance_sheet() -> None:
    wb = build_form1_balance_sheet_wb()
    assert detect_format(wb) == SoliqXltxFormat.FORM_1_BALANCE_SHEET


def test_detect_profit_tax() -> None:
    wb = build_profit_tax_wb()
    assert detect_format(wb) == SoliqXltxFormat.PROFIT_TAX


def test_empty_workbook_is_unknown() -> None:
    wb = Workbook()  # default Sheet, нет list01
    assert detect_format(wb) == SoliqXltxFormat.UNKNOWN


def test_workbook_without_list01_is_unknown() -> None:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Sheet1"
    wb.create_sheet("Other")
    assert detect_format(wb) == SoliqXltxFormat.UNKNOWN


def test_workbook_with_list01_but_no_signature_is_unknown() -> None:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "list01"
    ws["B3"] = "Что-то совершенно левое"
    assert detect_format(wb) == SoliqXltxFormat.UNKNOWN


def test_form1_takes_precedence_over_form2_when_both_sentinels_present() -> None:
    # Форма 1 проверяется раньше — если бы B3 содержал оба sentinel'а, выбираем Form 1.
    wb = build_form1_balance_sheet_wb()
    ws = wb["list01"]
    ws["B3"] = "Бухгалтерский баланс - форма № 1 (Отчет о финансовых результатах)"
    assert detect_format(wb) == SoliqXltxFormat.FORM_1_BALANCE_SHEET
