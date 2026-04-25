"""Тесты AssessDraftReadinessUseCase + source_trail mapper."""

from __future__ import annotations

from decimal import Decimal

from application.use_cases.assess_draft_readiness import (
    AssessDraftReadinessInput,
    assess_draft_readiness,
    source_trail_to_parser_sources,
)
from domain.services.data_readiness import (
    DataReadinessLevel,
    ParserSource,
)


def _empty_input() -> AssessDraftReadinessInput:
    return AssessDraftReadinessInput(
        annual_report_years=[],
        full_quarter_years=[],
        partial_quarter_years=[],
        source_trail={},
    )


# ===== source_trail_to_parser_sources =====


def test_source_trail_empty_returns_empty_set() -> None:
    assert source_trail_to_parser_sources({}) == set()


def test_source_trail_form1_assets_total_maps_to_form_1() -> None:
    sources = source_trail_to_parser_sources(
        {"form1.assets_total": "FORM_1 Q4 2025 (file.xltx)"}
    )
    assert sources == {ParserSource.FORM_1}


def test_source_trail_form1_liabilities_also_maps_to_form_1() -> None:
    sources = source_trail_to_parser_sources(
        {"form1.liabilities_total": "FORM_1 Q4 2025"}
    )
    assert sources == {ParserSource.FORM_1}


def test_source_trail_revenue_2025_maps_to_form_2() -> None:
    sources = source_trail_to_parser_sources(
        {"revenue_2025": "FORM_2 Q4 2025 (file.xltx)"}
    )
    assert sources == {ParserSource.FORM_2}


def test_source_trail_net_profit_2024_maps_to_form_2() -> None:
    sources = source_trail_to_parser_sources({"net_profit_2024": "FORM_2 Q4 2024"})
    assert sources == {ParserSource.FORM_2}


def test_source_trail_vat_declared_maps_to_vat_declaration() -> None:
    sources = source_trail_to_parser_sources({"vat_declared_2025": "VAT_DECL"})
    assert sources == {ParserSource.VAT_DECLARATION}


def test_source_trail_esf_prefix_maps_to_esf_csv() -> None:
    sources = source_trail_to_parser_sources({"esf_2025_q4": "ESF_CSV"})
    assert sources == {ParserSource.ESF_CSV}


def test_source_trail_profit_tax_maps_to_profit_tax() -> None:
    sources = source_trail_to_parser_sources({"profit_tax_2025": "PROFIT_TAX"})
    assert sources == {ParserSource.PROFIT_TAX}


def test_source_trail_combination_yields_multiple_sources() -> None:
    sources = source_trail_to_parser_sources(
        {
            "revenue_2024": "FORM_2",
            "revenue_2025": "FORM_2",
            "form1.assets_total": "FORM_1",
            "vat_declared_2025": "VAT",
        }
    )
    assert sources == {
        ParserSource.FORM_2,
        ParserSource.FORM_1,
        ParserSource.VAT_DECLARATION,
    }


def test_source_trail_unknown_keys_silently_ignored() -> None:
    """Future-proof: незнакомые ключи не падают."""
    sources = source_trail_to_parser_sources(
        {"unknown_key_xyz": "something", "revenue_2025": "FORM_2"}
    )
    assert sources == {ParserSource.FORM_2}


# ===== assess_draft_readiness — happy paths =====


def test_assess_empty_payload_yields_insufficient() -> None:
    report = assess_draft_readiness(_empty_input())
    assert report.level == DataReadinessLevel.INSUFFICIENT
    assert report.full_years == ()
    assert report.years_covered == ()
    assert report.confidence_score == Decimal(0)


def test_assess_one_annual_year_yields_minimal() -> None:
    report = assess_draft_readiness(
        AssessDraftReadinessInput(
            annual_report_years=[2025],
            full_quarter_years=[],
            partial_quarter_years=[],
            source_trail={},
        )
    )
    assert report.level == DataReadinessLevel.MINIMAL
    assert report.full_years == (2025,)


def test_assess_two_consecutive_years_yields_standard() -> None:
    report = assess_draft_readiness(
        AssessDraftReadinessInput(
            annual_report_years=[2024, 2025],
            full_quarter_years=[],
            partial_quarter_years=[],
            source_trail={"revenue_2024": "FORM_2", "revenue_2025": "FORM_2"},
        )
    )
    assert report.level == DataReadinessLevel.STANDARD
    assert ParserSource.FORM_2 in report.parser_sources


def test_assess_three_years_with_form1_and_esf_yields_comprehensive() -> None:
    report = assess_draft_readiness(
        AssessDraftReadinessInput(
            annual_report_years=[2023, 2024, 2025],
            full_quarter_years=[],
            partial_quarter_years=[],
            source_trail={
                "revenue_2025": "FORM_2",
                "form1.assets_total": "FORM_1",
                "esf_2025_q4": "ESF",
            },
        )
    )
    assert report.level == DataReadinessLevel.COMPREHENSIVE
    assert report.missing_capabilities == ()


def test_assess_full_quarters_count_as_full_year() -> None:
    """4 квартала за один год → year полный (без annual report)."""
    report = assess_draft_readiness(
        AssessDraftReadinessInput(
            annual_report_years=[],
            full_quarter_years=[2025],
            partial_quarter_years=[],
            source_trail={},
        )
    )
    assert report.level == DataReadinessLevel.MINIMAL
    assert report.full_years == (2025,)


def test_assess_partial_quarters_in_years_covered_not_full() -> None:
    """Partial квартал попадает в years_covered, но не в full_years."""
    report = assess_draft_readiness(
        AssessDraftReadinessInput(
            annual_report_years=[2025],
            full_quarter_years=[],
            partial_quarter_years=[2023],
            source_trail={},
        )
    )
    assert report.years_covered == (2023, 2025)
    assert report.full_years == (2025,)


def test_assess_one_year_via_yeartotal_proxy_yields_minimal() -> None:
    """Regression CA-035 smoke #2: на frontend заполнен только Q4 2025 (1 млрд),
    yearTotal даёт annual revenue → frontend builder кладёт год в
    annual_report_years (proxy для annual report). На application уровне это
    видно как обычный annual_report_years=[2025] → MINIMAL.

    Документирует контракт: при наличии годовой выручки (через sum квартальных
    ИЛИ annual cell) frontend translation НЕ должен передавать год как
    partial_quarter — иначе пользователь видит INSUFFICIENT при явно введённых
    данных. Тест на application уровне фиксирует ожидаемый contract от
    frontend (см. `web/.../checklist.tsx::buildRequest`).
    """
    report = assess_draft_readiness(
        AssessDraftReadinessInput(
            annual_report_years=[2025],
            full_quarter_years=[],
            partial_quarter_years=[],
            source_trail={},
        )
    )
    assert report.level == DataReadinessLevel.MINIMAL
    assert report.full_years == (2025,)
    assert report.confidence_score == Decimal("0.25")


def test_assess_duplicate_year_in_annual_and_full_quarters() -> None:
    """Год может быть указан и в annual и в full_quarter — попадает в full_years
    единожды (set-семантика на уровне domain)."""
    report = assess_draft_readiness(
        AssessDraftReadinessInput(
            annual_report_years=[2025],
            full_quarter_years=[2025],
            partial_quarter_years=[],
            source_trail={},
        )
    )
    assert report.full_years == (2025,)
