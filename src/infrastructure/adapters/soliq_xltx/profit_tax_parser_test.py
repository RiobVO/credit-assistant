"""Тесты парсера PROFIT_TAX (Расчёт налога на прибыль юридических лиц).

Best-effort семантика (CA-014): parser raises только на формат
(UnsupportedFormatError). Cell-level проблемы → warnings + None.

Реальные фикстуры `profit_tax_*_full.xltx` gitignored; smoke прогоняется
через `tests/parsers/real_xltx_test.py`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from domain.value_objects.money import Currency, Money
from infrastructure.adapters.soliq_xltx.errors import UnsupportedFormatError
from infrastructure.adapters.soliq_xltx.profit_tax_parser import (
    ProfitTaxData,
    parse_profit_tax,
)
from tests.fixtures.soliq_xltx._factories import (
    build_form2_income_statement_wb,
    build_profit_tax_wb,
    build_vat_declaration_wb,
)


def _uzs(amount: Decimal | int | float) -> Money:
    return Money(Decimal(str(amount)), Currency.UZS)


def test_parse_profit_tax_happy_path() -> None:
    """Defaults factory → распознаётся, taxable_profit + profit_tax_total в UZS ×1."""
    wb = build_profit_tax_wb(
        period_year=2025,
        period_quarter=4,
        taxable_profit_amount=211851159.0,
        profit_tax_total_amount=31777673.85,
    )

    result = parse_profit_tax(wb)

    assert isinstance(result, ProfitTaxData)
    assert result.taxable_profit == _uzs(Decimal("211851159"))
    assert result.profit_tax_total == _uzs(Decimal("31777673.85"))
    assert result.parse_warnings == []


def test_parse_profit_tax_header_propagated() -> None:
    """Header (year, quarter, ИНН) из existing _parse_profit_tax_header."""
    wb = build_profit_tax_wb(inn=305002665, period_year=2025, period_quarter=4)

    result = parse_profit_tax(wb)

    assert result.header.period_year == 2025
    assert result.header.period_index == 4
    assert result.header.period_kind == "quarter"
    assert result.header.borrower_inn is not None
    assert result.header.borrower_inn.value == "305002665"


def test_parse_profit_tax_negative_taxable_profit() -> None:
    """L31 убыток (отрицательное число) → Money с amount < 0 (signed)."""
    wb = build_profit_tax_wb(
        taxable_profit_amount=-146143099.0,
        profit_tax_total_amount=0.0,
    )

    result = parse_profit_tax(wb)

    assert result.taxable_profit == _uzs(Decimal("-146143099"))
    assert result.profit_tax_total == _uzs(Decimal("0"))


def test_parse_profit_tax_x_marker_silent() -> None:
    """'x' / None в money-cell → None без warning (штатный Soliq-маркер)."""
    wb = build_profit_tax_wb(
        taxable_profit_amount="x",
        profit_tax_total_amount=None,
    )

    result = parse_profit_tax(wb)

    assert result.taxable_profit is None
    assert result.profit_tax_total is None
    # 'x' и None — штатные маркеры, warnings не пишутся
    assert all("L31" not in w and "L39" not in w for w in result.parse_warnings)


def test_parse_profit_tax_garbage_cell_warns_and_returns_none() -> None:
    """Битый текст в L39 → warning + None, парсер не падает."""
    wb = build_profit_tax_wb(profit_tax_total_amount="мусор")

    result = parse_profit_tax(wb)

    assert result.profit_tax_total is None
    assert any("L39" in w and "мусор" in w for w in result.parse_warnings)


def test_parse_profit_tax_rejects_wrong_format() -> None:
    """FORM_2 в parse_profit_tax → UnsupportedFormatError."""
    wb = build_form2_income_statement_wb()

    with pytest.raises(UnsupportedFormatError):
        parse_profit_tax(wb)


def test_parse_profit_tax_rejects_vat_declaration() -> None:
    """VAT-декларация в parse_profit_tax → UnsupportedFormatError."""
    wb = build_vat_declaration_wb()

    with pytest.raises(UnsupportedFormatError):
        parse_profit_tax(wb)


def test_parse_profit_tax_missing_list01_raises() -> None:
    """list01 отсутствует → UnsupportedFormatError (структурная ошибка)."""
    wb = build_profit_tax_wb()
    del wb["list01"]

    with pytest.raises(UnsupportedFormatError):
        parse_profit_tax(wb)
