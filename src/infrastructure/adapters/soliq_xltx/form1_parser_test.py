"""Тесты парсера FORM_1 (Бухгалтерский баланс).

Best-effort семантика (CA-014/CA-029): parser raises только на формат
(UnsupportedFormatError). Cell-level проблемы → warnings + None.

Balance equation sanity (CA-029): расхождение A vs E+L > 0.5% от |A| → warning,
не raise. Smoke на реальной фикстуре `form1_q4_2025_201308534_full.xltx`
(QADR DON NON SAVDO, ИНН 201308534, Q4 2025) — gitignored.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from domain.value_objects.money import Currency, Money
from infrastructure.adapters.soliq_xltx.errors import UnsupportedFormatError
from infrastructure.adapters.soliq_xltx.form1_parser import (
    Form1BalanceSheetData,
    parse_form1,
)
from infrastructure.adapters.soliq_xltx.parser import SoliqXltxAdapter
from tests.fixtures.soliq_xltx._factories import (
    build_form1_balance_sheet_wb,
    build_vat_declaration_wb,
)

_REAL_FIXTURE = (
    Path(__file__).parents[4]
    / "tests/fixtures/soliq_xltx/form1_q4_2025_201308534_full.xltx"
)


def _uzs(amount: Decimal | int | float | str) -> Money:
    return Money(Decimal(str(amount)), Currency.UZS)


def test_total_assets_extracts_both_columns_in_uzs() -> None:
    """E54 → period_end, D54 → period_start. Источник в тыс. сум → × 1000."""
    wb = build_form1_balance_sheet_wb()

    result = parse_form1(wb)

    assert result.total_assets_period_end == _uzs(Decimal("2533084000"))
    assert result.total_assets_period_start == _uzs(Decimal("2087582000"))


def test_equity_and_liabilities_extracted() -> None:
    wb = build_form1_balance_sheet_wb()

    result = parse_form1(wb)

    assert result.equity_period_end == _uzs(Decimal("1548059000"))
    assert result.equity_period_start == _uzs(Decimal("1390777000"))
    assert result.total_liabilities_period_end == _uzs(Decimal("985025000"))
    assert result.long_term_liabilities_period_end == _uzs(Decimal("451600000"))
    assert result.short_term_liabilities_period_end == _uzs(Decimal("533425000"))


def test_total_debt_aggregates_five_components() -> None:
    """total_debt = 570+580+730+740+750. На дефолтной фикстуре:
    period_end = 451600 + 166667 = 618267 тыс. сум."""
    wb = build_form1_balance_sheet_wb()

    result = parse_form1(wb)

    assert result.total_debt_period_end == _uzs(Decimal("618267000"))
    assert result.total_debt_period_start == _uzs(Decimal("332222000"))


def test_total_debt_none_when_all_components_missing() -> None:
    """Все 5 долговых cells None → total_debt None (не Money(0))."""
    wb = build_form1_balance_sheet_wb(
        list02_cells={
            "D75": None, "E75": None,
            "D76": None, "E76": None,
            "D93": None, "E93": None,
            "D94": None, "E94": None,
            "D95": None, "E95": None,
        }
    )

    result = parse_form1(wb)

    assert result.total_debt_period_end is None
    assert result.total_debt_period_start is None


def test_total_debt_x_marker_treated_as_zero_in_aggregate() -> None:
    """'x' в долговой строке → пропуск (не активирует агрегат). Один реальный
    value среди четырёх 'x' → агрегат = это значение."""
    wb = build_form1_balance_sheet_wb(
        list02_cells={
            "D75": "x", "E75": "x",
            "D76": "x", "E76": 100000.0,
            "D93": "x", "E93": "x",
            "D94": "x", "E94": "x",
            "D95": "x", "E95": "x",
        }
    )

    result = parse_form1(wb)

    assert result.total_debt_period_end == _uzs(Decimal("100000000"))
    assert result.total_debt_period_start is None


def test_balance_equation_matches_silent() -> None:
    """Default fixture: A=E+L копейка в копейку → нет warning."""
    wb = build_form1_balance_sheet_wb()

    result = parse_form1(wb)

    assert not any("balance_equation_mismatch" in w for w in result.parse_warnings)


def test_balance_equation_mismatch_writes_warning() -> None:
    """A=1000, E+L=500 → delta 50% > 0.5% → warning с цифрами."""
    wb = build_form1_balance_sheet_wb(
        list02_cells={
            "E54": 1000.0,  # total_assets
            "E64": 300.0,   # equity
            "E97": 200.0,   # total_liabilities  (E+L=500, delta=500=50%)
        }
    )

    result = parse_form1(wb)

    mismatches = [w for w in result.parse_warnings if "balance_equation_mismatch" in w]
    assert len(mismatches) >= 1
    assert any("period_end" in w for w in mismatches)


def test_balance_equation_within_tolerance_silent() -> None:
    """A=200000, E+L=200900 → delta 0.45% < 0.5% → silent."""
    wb = build_form1_balance_sheet_wb(
        list02_cells={
            "E54": 200000.0,
            "E64": 100000.0,
            "E97": 100900.0,  # 0.45% mismatch
        }
    )

    result = parse_form1(wb)

    assert not any(
        "balance_equation_mismatch" in w and "period_end" in w
        for w in result.parse_warnings
    )


def test_balance_equation_skipped_when_component_missing() -> None:
    """Если total_assets/equity/liabilities = None → check пропущен без warning."""
    wb = build_form1_balance_sheet_wb(
        list02_cells={"E54": None}  # total_assets period_end missing
    )

    result = parse_form1(wb)

    assert result.total_assets_period_end is None
    assert not any(
        "balance_equation_mismatch" in w and "period_end" in w
        for w in result.parse_warnings
    )


def test_x_marker_in_money_cell_yields_none_silently() -> None:
    """'x' в money-cell → None без warning (штатный маркер «неприменимо»)."""
    wb = build_form1_balance_sheet_wb(list02_cells={"E10": "x"})

    result = parse_form1(wb)

    assert result.fixed_assets_period_end is None
    assert all("E10" not in w for w in result.parse_warnings)


def test_garbage_cell_writes_warning_returns_none() -> None:
    """Битый текст в money-cell → warning + None, парсер не падает."""
    wb = build_form1_balance_sheet_wb(list02_cells={"E10": "мусор"})

    result = parse_form1(wb)

    assert result.fixed_assets_period_end is None
    assert any("E10" in w and "мусор" in w for w in result.parse_warnings)


def test_bool_cell_writes_warning_returns_none() -> None:
    """bool — подкласс int, парсер должен явно отсечь как unsupported."""
    wb = build_form1_balance_sheet_wb(list02_cells={"E10": True})

    result = parse_form1(wb)

    assert result.fixed_assets_period_end is None
    assert any("E10" in w and "bool" in w for w in result.parse_warnings)


def test_wrong_format_raises() -> None:
    """VAT-декларация в parse_form1 → UnsupportedFormatError."""
    wb = build_vat_declaration_wb()

    with pytest.raises(UnsupportedFormatError):
        parse_form1(wb)


def test_missing_list02_raises() -> None:
    """list02 отсутствует → UnsupportedFormatError (структурная ошибка)."""
    wb = build_form1_balance_sheet_wb()
    del wb["list02"]

    with pytest.raises(UnsupportedFormatError, match="list02"):
        parse_form1(wb)


def test_header_year_and_quarter_propagated() -> None:
    """Header (year, quarter, ИНН, org) приходит из existing _parse_form1_header."""
    wb = build_form1_balance_sheet_wb(period_year=2024, period_quarter=3)

    result = parse_form1(wb)

    assert result.header.period_year == 2024
    assert result.header.period_index == 3
    assert result.header.period_kind == "quarter"
    assert result.header.borrower_inn is not None
    assert result.header.borrower_inn.value == "306399449"


def test_adapter_dispatch_returns_form1_data() -> None:
    """SoliqXltxAdapter.parse распознаёт FORM_1 и вызывает parse_form1."""
    from io import BytesIO

    wb = build_form1_balance_sheet_wb()
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    result = SoliqXltxAdapter().parse(buf.read())

    assert isinstance(result, Form1BalanceSheetData)
    assert result.total_assets_period_end is not None


@pytest.mark.skipif(not _REAL_FIXTURE.exists(), reason="real FORM_1 fixture not present")
def test_real_fixture_smoke() -> None:
    """Реальный xltx папы (Q4 2025, QADR DON NON SAVDO, ИНН 201308534) — парсится
    без исключений, балансовое равенство сходится копейка в копейку, total_debt
    = 580+730 = 451600+166667 = 618267 тыс. сум.
    """
    raw = _REAL_FIXTURE.read_bytes()

    result = SoliqXltxAdapter().parse(raw)

    assert isinstance(result, Form1BalanceSheetData)
    assert result.header.borrower_inn is not None
    assert result.header.borrower_inn.value == "201308534"
    assert result.header.period_year == 2025
    assert result.header.period_index == 4
    assert result.total_assets_period_end == _uzs(Decimal("2533084000"))
    assert result.total_assets_period_start == _uzs(Decimal("2087582000"))
    assert result.equity_period_end == _uzs(Decimal("1548059000"))
    assert result.total_liabilities_period_end == _uzs(Decimal("985025000"))
    assert result.total_debt_period_end == _uzs(Decimal("618267000"))
    assert result.total_debt_period_start == _uzs(Decimal("332222000"))
    # Balance equation: ровно, без warning
    assert not any("balance_equation_mismatch" in w for w in result.parse_warnings)
