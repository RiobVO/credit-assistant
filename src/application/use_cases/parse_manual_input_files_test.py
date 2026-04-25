"""Тесты ParseManualInputFilesUseCase.

Best-effort оркестратор: классифицирует пачку файлов, мерджит результаты в
``ParsedFinancials``. Не raises — только warnings.
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

import pytest

from application.use_cases.parse_manual_input_files import (
    NamedFile,
    ParseManualInputFilesUseCase,
)
from infrastructure.adapters.soliq_xltx.parser import SoliqXltxAdapter
from tests.fixtures.soliq_xltx._factories import (
    build_form1_balance_sheet_wb,
    build_form2_income_statement_wb,
    build_vat_declaration_wb,
    build_vat_registry_wb,
)


def _bytes(wb: object) -> bytes:
    buf = BytesIO()
    wb.save(buf)  # type: ignore[attr-defined]
    buf.seek(0)
    return buf.read()


@pytest.fixture
def usecase() -> ParseManualInputFilesUseCase:
    return ParseManualInputFilesUseCase(adapter=SoliqXltxAdapter())


def test_single_form2_q4_fills_two_years_annual(usecase: ParseManualInputFilesUseCase) -> None:
    """FORM_2 за Q4 2025 → revenue/net_profit заполняются за 2025 и 2024 (prior column)."""
    content = _bytes(
        build_form2_income_statement_wb(
            period_year=2025,
            period_quarter=4,
            revenue_current=5973686.0,  # тыс. сум
            revenue_prior=6559649.0,
            net_profit_current=(43697.0, 0.0),
            net_profit_prior=(0.0, 136022.0),  # убыток в прошлом году
        )
    )

    result = usecase.execute([NamedFile(name="form2.xltx", content=content)])

    assert result.revenue_by_year == {
        2025: Decimal("5973686000"),
        2024: Decimal("6559649000"),
    }
    assert result.net_profit_by_year == {
        2025: Decimal("43697000"),
        2024: Decimal("-136022000"),
    }
    assert "revenue_2025" in result.source_trail
    assert "FORM_2 Q4 2025" in result.source_trail["revenue_2025"]
    assert result.parse_warnings == []


def test_form2_non_q4_skipped_with_warning(usecase: ParseManualInputFilesUseCase) -> None:
    """FORM_2 за Q1/Q2/Q3 — YTD меньше года, в CA-027 не используется."""
    content = _bytes(build_form2_income_statement_wb(period_year=2025, period_quarter=2))

    result = usecase.execute([NamedFile(name="form2_q2.xltx", content=content)])

    assert result.revenue_by_year == {}
    assert any("Q2" in w and "пропуск" in w for w in result.parse_warnings)


def test_vat_declaration_fills_vat_declared_by_year(usecase: ParseManualInputFilesUseCase) -> None:
    content = _bytes(
        build_vat_declaration_wb(
            period_year=2026,
            sales_total_vat=62799985.69,
        )
    )

    result = usecase.execute([NamedFile(name="vat.xltx", content=content)])

    # Decimal сохраняет дробную часть (vat_charged_total не округляется)
    assert 2026 in result.vat_declared_by_year
    assert "vat_declared_2026" in result.source_trail


def test_form1_fills_assets_and_liabilities(usecase: ParseManualInputFilesUseCase) -> None:
    """CA-041: FORM_1 заполняет assets_total + liabilities_total из column E
    (период_end) и assets/liabilities_period_start из column D.

    Дефолтная фикстура: E54=2533084 (тыс. сум), E97=985025; D54=2087582,
    D97=696805. ×1000 → UZS. source_trail обогащается form1.* ключами.
    """
    content = _bytes(build_form1_balance_sheet_wb(period_year=2025, period_quarter=4))

    result = usecase.execute([NamedFile(name="form1.xltx", content=content)])

    assert result.assets_total == Decimal("2533084000")
    assert result.liabilities_total == Decimal("985025000")
    assert result.assets_total_period_start == Decimal("2087582000")
    assert result.liabilities_total_period_start == Decimal("696805000")
    assert "form1.assets_total" in result.source_trail
    assert "form1.liabilities_total" in result.source_trail
    assert "form1.assets_total_period_start" in result.source_trail
    assert "form1.liabilities_total_period_start" in result.source_trail
    assert "FORM_1 Q4 2025" in result.source_trail["form1.assets_total"]
    assert "form1.xltx" in result.source_trail["form1.assets_total"]


def test_form1_latest_period_wins_silently(usecase: ParseManualInputFilesUseCase) -> None:
    """Q4 2024 + Q4 2025 → побеждает Q4 2025 (свежий срез). Без warning —
    это ожидаемое поведение для balance sheet, не конфликт.
    """
    older = _bytes(
        build_form1_balance_sheet_wb(
            period_year=2024,
            period_quarter=4,
            list02_cells={"E54": 1.0, "E97": 1.0, "D54": 1.0, "D97": 1.0},
        )
    )
    newer = _bytes(
        build_form1_balance_sheet_wb(
            period_year=2025,
            period_quarter=4,
            list02_cells={"E54": 2.0, "E97": 2.0, "D54": 2.0, "D97": 2.0},
        )
    )

    # Порядок: новый сначала, потом старый — старый должен проиграть с warning.
    result = usecase.execute(
        [
            NamedFile(name="newer.xltx", content=newer),
            NamedFile(name="older.xltx", content=older),
        ]
    )

    assert result.assets_total == Decimal("2000")  # 2.0 × 1000
    assert result.liabilities_total == Decimal("2000")
    assert "FORM_1 Q4 2025" in result.source_trail["form1.assets_total"]
    assert any("older.xltx" in w and "пропуск" in w for w in result.parse_warnings)


def test_form1_latest_period_wins_when_order_reversed(
    usecase: ParseManualInputFilesUseCase,
) -> None:
    """Старый файл сначала, новый потом — новый вытесняет, без warning."""
    older = _bytes(
        build_form1_balance_sheet_wb(
            period_year=2024,
            period_quarter=4,
            list02_cells={"E54": 1.0, "E97": 1.0, "D54": 1.0, "D97": 1.0},
        )
    )
    newer = _bytes(
        build_form1_balance_sheet_wb(
            period_year=2025,
            period_quarter=4,
            list02_cells={"E54": 2.0, "E97": 2.0, "D54": 2.0, "D97": 2.0},
        )
    )

    result = usecase.execute(
        [
            NamedFile(name="older.xltx", content=older),
            NamedFile(name="newer.xltx", content=newer),
        ]
    )

    assert result.assets_total == Decimal("2000")
    assert "FORM_1 Q4 2025" in result.source_trail["form1.assets_total"]
    # Свежий вытеснил старого тихо — это не конфликт.
    assert not any("пропуск" in w for w in result.parse_warnings)


def test_form1_same_period_first_wins_with_warning(
    usecase: ParseManualInputFilesUseCase,
) -> None:
    """Два FORM_1 за тот же (year, quarter) → first wins + дубликат-warning."""
    first = _bytes(
        build_form1_balance_sheet_wb(
            period_year=2025,
            period_quarter=4,
            list02_cells={"E54": 100.0, "E97": 100.0, "D54": 100.0, "D97": 100.0},
        )
    )
    second = _bytes(
        build_form1_balance_sheet_wb(
            period_year=2025,
            period_quarter=4,
            list02_cells={"E54": 999.0, "E97": 999.0, "D54": 999.0, "D97": 999.0},
        )
    )

    result = usecase.execute(
        [
            NamedFile(name="first.xltx", content=first),
            NamedFile(name="second.xltx", content=second),
        ]
    )

    assert result.assets_total == Decimal("100000")
    assert any(
        "тот же период" in w and "second.xltx" in w for w in result.parse_warnings
    )


def test_unknown_garbage_file_warns(usecase: ParseManualInputFilesUseCase) -> None:
    """Битый бинарник → warning «не удалось открыть», use case не падает."""
    result = usecase.execute([NamedFile(name="trash.bin", content=b"\x00\x01junk")])

    assert any("trash.bin" in w for w in result.parse_warnings)


def test_mixed_batch_form2_and_vat(usecase: ParseManualInputFilesUseCase) -> None:
    """FORM_2 Q4 2025 + VAT 2025 — оба сливаются в один ParsedFinancials."""
    form2 = _bytes(build_form2_income_statement_wb(period_year=2025, period_quarter=4))
    vat = _bytes(build_vat_declaration_wb(period_year=2025))

    result = usecase.execute(
        [
            NamedFile(name="form2.xltx", content=form2),
            NamedFile(name="vat.xltx", content=vat),
        ]
    )

    assert 2025 in result.revenue_by_year
    assert 2025 in result.vat_declared_by_year
    assert "FORM_2" in result.source_trail["revenue_2025"]
    assert "VAT_DECLARATION" in result.source_trail["vat_declared_2025"]


def test_duplicate_year_form2_keeps_first(usecase: ParseManualInputFilesUseCase) -> None:
    """Две FORM_2 за один год → первая побеждает, конфликт-warning."""
    first = _bytes(
        build_form2_income_statement_wb(period_year=2025, revenue_current=100.0)
    )
    second = _bytes(
        build_form2_income_statement_wb(period_year=2025, revenue_current=999.0)
    )

    result = usecase.execute(
        [
            NamedFile(name="first.xltx", content=first),
            NamedFile(name="second.xltx", content=second),
        ]
    )

    # Первый файл выиграл — 100 тыс. → 100_000 UZS
    assert result.revenue_by_year[2025] == Decimal("100000")
    assert any("уже было заполнено" in w for w in result.parse_warnings)


def test_vat_registry_ilova_quietly_skipped(usecase: ParseManualInputFilesUseCase) -> None:
    """Реестр счетов-фактур не несёт financial-полей — скип без warning."""
    content = _bytes(build_vat_registry_wb())

    result = usecase.execute([NamedFile(name="ilova.xltx", content=content)])

    assert result.revenue_by_year == {}
    # Реестр валиден, не должно быть warnings (тихий скип).
    assert result.parse_warnings == []


def test_ca037_form2_fills_pbt_and_interest_expense_for_both_years(
    usecase: ParseManualInputFilesUseCase,
) -> None:
    """CA-037: FORM_2 за Q4 заполняет profit_before_tax_by_year и
    interest_expense_by_year — для текущего года из current column и для
    предыдущего из prior column. Source_trail обогащается соответствующими
    ключами.
    """
    content = _bytes(
        build_form2_income_statement_wb(
            period_year=2025,
            period_quarter=4,
            # PBT: current 63358 (income=63358, expense=0) → +63358
            #      prior   −124633 (income=0, expense=124633) → −124633
            profit_before_tax_current=(63358.0, 0.0),
            profit_before_tax_prior=(0.0, 124633.0),
            interest_expense_current=40088.0,
            interest_expense_prior=158407.0,
        )
    )

    result = usecase.execute([NamedFile(name="form2.xltx", content=content)])

    assert result.profit_before_tax_by_year == {
        2025: Decimal("63358000"),
        2024: Decimal("-124633000"),
    }
    assert result.interest_expense_by_year == {
        2025: Decimal("40088000"),
        2024: Decimal("158407000"),
    }
    assert "profit_before_tax_2025" in result.source_trail
    assert "interest_expense_2025" in result.source_trail
    assert "profit_before_tax_2024" in result.source_trail
    assert "interest_expense_2024" in result.source_trail
    assert "FORM_2 Q4 2025" in result.source_trail["profit_before_tax_2025"]


def test_ca037_form1_fills_equity_and_total_debt_both_periods(
    usecase: ParseManualInputFilesUseCase,
) -> None:
    """CA-037: FORM_1 wiring расширяется equity/total_debt на конец и начало
    отчётного периода. Дефолтная фикстура:
    * E64 = 1 548 059 тыс. сум → equity_period_end = 1 548 059 000 UZS
    * D64 = 1 390 777 → equity_period_start = 1 390 777 000
    * total_debt_end = 451600 + 166667 = 618 267 тыс. → 618 267 000
    * total_debt_start = 110000 + 222222 = 332 222 тыс. → 332 222 000

    source_trail обогащается ключами ``form1.equity`` / ``form1.total_debt``
    плюс period_start версии — согласовано с префикс-маппером CA-035
    assess_draft_readiness.
    """
    content = _bytes(build_form1_balance_sheet_wb(period_year=2025, period_quarter=4))

    result = usecase.execute([NamedFile(name="form1.xltx", content=content)])

    assert result.equity_period_end == Decimal("1548059000")
    assert result.equity_period_start == Decimal("1390777000")
    assert result.total_debt_period_end == Decimal("618267000")
    assert result.total_debt_period_start == Decimal("332222000")
    assert "form1.equity" in result.source_trail
    assert "form1.equity_period_start" in result.source_trail
    assert "form1.total_debt" in result.source_trail
    assert "form1.total_debt_period_start" in result.source_trail
    assert "FORM_1 Q4 2025" in result.source_trail["form1.equity"]


def test_empty_input_returns_empty_parsed(usecase: ParseManualInputFilesUseCase) -> None:
    result = usecase.execute([])

    assert result.revenue_by_year == {}
    assert result.parse_warnings == []
    assert result.source_trail == {}
