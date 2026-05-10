"""Тесты парсера FORM_2 (Отчёт о финансовых результатах).

Best-effort семантика (CA-014): parser raises только на формат
(UnsupportedFormatError). Cell-level проблемы → warnings + None.

Реальная фикстура `form2_q4_2025_full.xltx` gitignored; smoke прогоняется
если файл присутствует локально.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from domain.value_objects.money import Currency, Money
from infrastructure.adapters.soliq_xltx.errors import UnsupportedFormatError
from infrastructure.adapters.soliq_xltx.form2_parser import (
    Form2IncomeStatementData,
    parse_form2,
)
from infrastructure.adapters.soliq_xltx.parser import SoliqXltxAdapter
from tests.fixtures.soliq_xltx._factories import (
    build_form2_income_statement_wb,
    build_vat_declaration_wb,
)

_REAL_FIXTURE = Path(__file__).parents[4] / "tests/fixtures/soliq_xltx/form2_q4_2025_full.xltx"


def _uzs(amount: Decimal | int | float) -> Money:
    return Money(Decimal(str(amount)), Currency.UZS)


def test_revenue_extracts_current_and_prior_in_uzs() -> None:
    """Выручка row 6: F6 → current, D6 → prior. Источник в тыс. сум → × 1000."""
    wb = build_form2_income_statement_wb(
        revenue_prior=6559649.0,
        revenue_current=5973686.0,
    )

    result = parse_form2(wb)

    assert result.revenue_current_period == _uzs(Decimal("5973686000"))
    assert result.revenue_prior_year_period == _uzs(Decimal("6559649000"))


def test_net_profit_signed_profit_case() -> None:
    """Прибыль: F=43697, G=0 → +43697×1000."""
    wb = build_form2_income_statement_wb(
        net_profit_current=(43697.0, 0.0),
        net_profit_prior=(0.0, 0.0),
    )

    result = parse_form2(wb)

    assert result.net_profit_current == _uzs(Decimal("43697000"))
    assert result.net_profit_prior_year == _uzs(Decimal("0"))


def test_net_profit_signed_loss_case() -> None:
    """Убыток: D=0, E=136022 → −136022×1000 (отрицательное Money)."""
    wb = build_form2_income_statement_wb(
        net_profit_prior=(0.0, 136022.0),
        net_profit_current=(0.0, 0.0),
    )

    result = parse_form2(wb)

    assert result.net_profit_prior_year == _uzs(Decimal("-136022000"))
    assert result.net_profit_current == _uzs(Decimal("0"))


def test_signed_pair_both_missing_returns_none() -> None:
    """Если обе ячейки signed пары — 'x' или None — возвращаем None (нет данных)."""
    wb = build_form2_income_statement_wb(
        net_profit_current=("x", "x"),
        net_profit_prior=(None, None),
    )

    result = parse_form2(wb)

    assert result.net_profit_current is None
    assert result.net_profit_prior_year is None


def test_bonus_fields_extract() -> None:
    """cost_of_sales (G7), interest_expense (G23), profit_tax (G30)."""
    wb = build_form2_income_statement_wb(
        cost_current=5037111.0,
        interest_expense_current=40088.0,
        profit_tax_current=19661.0,
        gross_profit_current=936575.0,
        operating_profit_current=(87086.0, 0.0),
        profit_before_tax_current=(63358.0, 0.0),
    )

    result = parse_form2(wb)

    assert result.cost_of_sales_current == _uzs(Decimal("5037111000"))
    assert result.interest_expense_current == _uzs(Decimal("40088000"))
    assert result.profit_tax_current == _uzs(Decimal("19661000"))
    assert result.gross_profit_current == _uzs(Decimal("936575000"))
    assert result.operating_profit_current == _uzs(Decimal("87086000"))
    assert result.profit_before_tax_current == _uzs(Decimal("63358000"))


def test_x_marker_in_income_column_yields_none() -> None:
    """'x' в income column → revenue None (best-effort, не raise)."""
    wb = build_form2_income_statement_wb(
        revenue_current="x",
        revenue_prior="x",
    )

    result = parse_form2(wb)

    assert result.revenue_current_period is None
    assert result.revenue_prior_year_period is None
    # 'x' — штатный маркер, warnings не пишутся для него
    assert all("D6" not in w and "F6" not in w for w in result.parse_warnings)


def test_garbage_cell_writes_warning_returns_none() -> None:
    """Битый текст в money-cell → warning + None, парсер не падает."""
    wb = build_form2_income_statement_wb(revenue_current="мусор")

    result = parse_form2(wb)

    assert result.revenue_current_period is None
    assert any("F6" in w and "мусор" in w for w in result.parse_warnings)


def test_wrong_format_raises() -> None:
    """VAT-декларация в parse_form2 → UnsupportedFormatError."""
    wb = build_vat_declaration_wb()

    with pytest.raises(UnsupportedFormatError):
        parse_form2(wb)


def test_missing_list02_raises() -> None:
    """list02 отсутствует → UnsupportedFormatError (структурная ошибка)."""
    wb = build_form2_income_statement_wb()
    del wb["list02"]

    with pytest.raises(UnsupportedFormatError, match="list02"):
        parse_form2(wb)


def test_header_year_and_quarter_propagated() -> None:
    """Header (year, quarter, ИНН, org) приходит из existing _parse_form2_header."""
    wb = build_form2_income_statement_wb(period_year=2024, period_quarter=3)

    result = parse_form2(wb)

    assert result.header.period_year == 2024
    assert result.header.period_index == 3
    assert result.header.period_kind == "quarter"
    assert result.header.borrower_inn is not None
    assert result.header.borrower_inn.value == "306399449"


def test_adapter_dispatch_returns_form2_data() -> None:
    """SoliqXltxAdapter.parse распознаёт FORM_2 и вызывает parse_form2."""
    from io import BytesIO

    wb = build_form2_income_statement_wb()
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    result = SoliqXltxAdapter().parse(buf.read())

    assert isinstance(result, Form2IncomeStatementData)
    assert result.revenue_current_period is not None


@pytest.mark.skipif(not _REAL_FIXTURE.exists(), reason="real FORM_2 fixture not present")
def test_real_fixture_smoke() -> None:
    """Реальный xltx папы (Q4 2025) — парсится без исключений, ключевые поля есть.

    Числа из dump: F6=5973686, D6=6559649, F32=43697, D32=0/E32=136022.
    Все суммы × 1000.
    """
    raw = _REAL_FIXTURE.read_bytes()

    result = SoliqXltxAdapter().parse(raw)

    assert isinstance(result, Form2IncomeStatementData)
    assert result.revenue_current_period == _uzs(Decimal("5973686000"))
    assert result.revenue_prior_year_period == _uzs(Decimal("6559649000"))
    assert result.net_profit_current == _uzs(Decimal("43697000"))
    assert result.net_profit_prior_year == _uzs(Decimal("-136022000"))
    assert result.header.period_year == 2025
    assert result.header.period_index == 4
    assert result.header.borrower_inn is not None
    assert result.header.borrower_inn.value == "306399449"
