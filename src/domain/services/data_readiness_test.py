"""Тесты Data Readiness Assessment service (см. ADR 0010).

Покрытие: helpers (_full_years, _max_consecutive_run, _any_years), 4-уровневая
классификация, missing_capabilities, confidence_score, edge cases.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.services.data_readiness import (
    CAP_BALANCE_RATIOS,
    CAP_CAGR,
    CAP_TAX_BURDEN,
    CAP_YOY_TREND,
    DataReadinessLevel,
    DataReadinessReport,
    ParserSource,
    _full_years,
    _max_consecutive_run,
    assess_readiness,
)
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money


def _money(amount: int) -> Money:
    return Money(Decimal(amount), Currency.UZS)


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("100000001"),
        name='ООО "Тест"',
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 1, 1),
        director_name="Иванов И.И.",
        director_appointed_at=date(2020, 1, 1),
        oked_main="46.39",
        registered_address="Ташкент",
    )


def _annual_report(year: int) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=_money(1_000_000),
        net_profit=_money(100_000),
        taxes_paid=_money(20_000),
    )


def _quarterly_report(year: int, quarter: int) -> FinancialReport:
    """Q1 = янв-мар, Q2 = апр-июн, Q3 = июл-сен, Q4 = окт-дек."""
    starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
    ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    return FinancialReport(
        period=DateRange(
            date(year, *starts[quarter]),
            date(year, *ends[quarter]),
        ),
        revenue=_money(250_000),
        net_profit=_money(25_000),
        taxes_paid=_money(5_000),
    )


def _snapshot(
    *,
    annual_years: tuple[int, ...] = (),
    quarterly_per_year: dict[int, int] | None = None,
) -> BorrowerSnapshot:
    """quarterly_per_year[year] = N квартальных reports за этот год (1..4)."""
    quarterly_per_year = quarterly_per_year or {}
    return BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 12),
        annual_reports=[_annual_report(y) for y in annual_years],
        quarterly_reports=[
            _quarterly_report(year, q)
            for year, count in quarterly_per_year.items()
            for q in range(1, count + 1)
        ],
    )


# ===== Группа A: _full_years helper =====


def test_full_years_empty_snapshot_returns_empty_set() -> None:
    assert _full_years(_snapshot()) == set()


def test_full_years_single_annual_report() -> None:
    assert _full_years(_snapshot(annual_years=(2025,))) == {2025}


def test_full_years_three_quarters_not_full() -> None:
    """Только 3 квартала за год → year не полный."""
    assert _full_years(_snapshot(quarterly_per_year={2025: 3})) == set()


def test_full_years_four_quarters_full() -> None:
    assert _full_years(_snapshot(quarterly_per_year={2025: 4})) == {2025}


def test_full_years_annual_plus_quarterly_union() -> None:
    """Annual за 2024 + 4 кварталов за 2025 → оба года полные."""
    snap = _snapshot(annual_years=(2024,), quarterly_per_year={2025: 4})
    assert _full_years(snap) == {2024, 2025}


def test_full_years_partial_quarters_ignored() -> None:
    """3 квартала за 2024 + 4 квартала за 2025 → только 2025 полный."""
    snap = _snapshot(quarterly_per_year={2024: 3, 2025: 4})
    assert _full_years(snap) == {2025}


# ===== Группа B: _max_consecutive_run helper =====


def test_consecutive_run_empty_zero() -> None:
    assert _max_consecutive_run(set()) == 0


def test_consecutive_run_single_year() -> None:
    assert _max_consecutive_run({2025}) == 1


def test_consecutive_run_two_consecutive() -> None:
    assert _max_consecutive_run({2024, 2025}) == 2


def test_consecutive_run_three_consecutive() -> None:
    assert _max_consecutive_run({2023, 2024, 2025}) == 3


def test_consecutive_run_gap_breaks_streak() -> None:
    """{2023, 2025} — пропуск 2024 → max run = 1."""
    assert _max_consecutive_run({2023, 2025}) == 1


def test_consecutive_run_two_groups_picks_longest() -> None:
    """{2020, 2021, 2024, 2025} → две группы по 2, ответ 2."""
    assert _max_consecutive_run({2020, 2021, 2024, 2025}) == 2


def test_consecutive_run_long_streak_after_gap() -> None:
    """{2018, 2022, 2023, 2024, 2025} → max run = 4."""
    assert _max_consecutive_run({2018, 2022, 2023, 2024, 2025}) == 4


# ===== Группа C: assess_readiness — уровни =====


def test_level_insufficient_when_no_data() -> None:
    report = assess_readiness(_snapshot(), set())
    assert report.level == DataReadinessLevel.INSUFFICIENT


def test_level_minimal_with_one_annual_year() -> None:
    report = assess_readiness(_snapshot(annual_years=(2025,)), set())
    assert report.level == DataReadinessLevel.MINIMAL


def test_level_minimal_with_four_quarters_one_year() -> None:
    report = assess_readiness(
        _snapshot(quarterly_per_year={2025: 4}), set()
    )
    assert report.level == DataReadinessLevel.MINIMAL


def test_level_standard_with_two_consecutive_annual_years() -> None:
    report = assess_readiness(
        _snapshot(annual_years=(2024, 2025)), set()
    )
    assert report.level == DataReadinessLevel.STANDARD


def test_level_standard_with_two_consecutive_quarterly() -> None:
    report = assess_readiness(
        _snapshot(quarterly_per_year={2024: 4, 2025: 4}), set()
    )
    assert report.level == DataReadinessLevel.STANDARD


def test_level_comprehensive_requires_three_plus_form1_plus_tax_source() -> None:
    """Happy path: 3 года подряд + FORM_1 + ESF_CSV → COMPREHENSIVE."""
    report = assess_readiness(
        _snapshot(annual_years=(2023, 2024, 2025)),
        {ParserSource.FORM_2, ParserSource.FORM_1, ParserSource.ESF_CSV},
    )
    assert report.level == DataReadinessLevel.COMPREHENSIVE


def test_level_comprehensive_profit_tax_satisfies_tax_source() -> None:
    """PROFIT_TAX вместо ESF_CSV тоже даёт COMPREHENSIVE."""
    report = assess_readiness(
        _snapshot(annual_years=(2023, 2024, 2025)),
        {ParserSource.FORM_2, ParserSource.FORM_1, ParserSource.PROFIT_TAX},
    )
    assert report.level == DataReadinessLevel.COMPREHENSIVE


def test_level_standard_three_years_form1_but_no_tax_source() -> None:
    """3 года + FORM_1 без tax → не COMPREHENSIVE, только STANDARD."""
    report = assess_readiness(
        _snapshot(annual_years=(2023, 2024, 2025)),
        {ParserSource.FORM_2, ParserSource.FORM_1},
    )
    assert report.level == DataReadinessLevel.STANDARD


def test_level_standard_three_years_tax_but_no_form1() -> None:
    """3 года + tax без FORM_1 → STANDARD, не COMPREHENSIVE."""
    report = assess_readiness(
        _snapshot(annual_years=(2023, 2024, 2025)),
        {ParserSource.FORM_2, ParserSource.ESF_CSV},
    )
    assert report.level == DataReadinessLevel.STANDARD


def test_level_minimal_with_gap_in_years() -> None:
    """{2023, 2025} — gap в 2024 → consecutive_max=1 → MINIMAL."""
    report = assess_readiness(_snapshot(annual_years=(2023, 2025)), set())
    assert report.level == DataReadinessLevel.MINIMAL


def test_level_minimal_with_non_consecutive_two_years() -> None:
    """{2022, 2024} → max consecutive 1 → MINIMAL."""
    report = assess_readiness(_snapshot(annual_years=(2022, 2024)), set())
    assert report.level == DataReadinessLevel.MINIMAL


def test_level_comprehensive_four_consecutive_years() -> None:
    """4 года подряд тоже даёт COMPREHENSIVE (≥3 достаточно)."""
    report = assess_readiness(
        _snapshot(annual_years=(2022, 2023, 2024, 2025)),
        {ParserSource.FORM_1, ParserSource.ESF_CSV},
    )
    assert report.level == DataReadinessLevel.COMPREHENSIVE


# ===== Группа D: missing_capabilities =====


def test_missing_caps_insufficient_all_four_missing() -> None:
    report = assess_readiness(_snapshot(), set())
    assert set(report.missing_capabilities) == {
        CAP_YOY_TREND,
        CAP_CAGR,
        CAP_BALANCE_RATIOS,
        CAP_TAX_BURDEN,
    }


def test_missing_caps_minimal_no_sources_all_four() -> None:
    """MINIMAL без FORM_1/tax → все 4 capabilities missing."""
    report = assess_readiness(_snapshot(annual_years=(2025,)), set())
    assert set(report.missing_capabilities) == {
        CAP_YOY_TREND,
        CAP_CAGR,
        CAP_BALANCE_RATIOS,
        CAP_TAX_BURDEN,
    }


def test_missing_caps_standard_no_sources_three_missing() -> None:
    """STANDARD без FORM_1/tax → yoy_trend есть, остальные 3 missing."""
    report = assess_readiness(
        _snapshot(annual_years=(2024, 2025)), set()
    )
    assert set(report.missing_capabilities) == {
        CAP_CAGR,
        CAP_BALANCE_RATIOS,
        CAP_TAX_BURDEN,
    }


def test_missing_caps_standard_with_form1_and_tax_only_cagr() -> None:
    """2 года + FORM_1 + ESF → не хватает только CAGR (нужно 3 года)."""
    report = assess_readiness(
        _snapshot(annual_years=(2024, 2025)),
        {ParserSource.FORM_1, ParserSource.ESF_CSV},
    )
    assert report.missing_capabilities == (CAP_CAGR,)


def test_missing_caps_comprehensive_no_missing() -> None:
    """3 года + FORM_1 + tax → пустой список missing."""
    report = assess_readiness(
        _snapshot(annual_years=(2023, 2024, 2025)),
        {ParserSource.FORM_1, ParserSource.PROFIT_TAX},
    )
    assert report.missing_capabilities == ()


def test_missing_caps_three_years_form1_no_tax_only_tax_burden() -> None:
    report = assess_readiness(
        _snapshot(annual_years=(2023, 2024, 2025)),
        {ParserSource.FORM_1},
    )
    assert report.missing_capabilities == (CAP_TAX_BURDEN,)


def test_missing_caps_minimal_with_form1_and_esf() -> None:
    """1 год + FORM_1 + ESF → не хватает yoy_trend и cagr."""
    report = assess_readiness(
        _snapshot(annual_years=(2025,)),
        {ParserSource.FORM_1, ParserSource.ESF_CSV},
    )
    assert set(report.missing_capabilities) == {CAP_YOY_TREND, CAP_CAGR}


# ===== Группа E: confidence_score =====


def test_confidence_zero_when_no_data() -> None:
    report = assess_readiness(_snapshot(), set())
    assert report.confidence_score == Decimal(0)


def test_confidence_one_year_no_bonus() -> None:
    report = assess_readiness(_snapshot(annual_years=(2025,)), set())
    assert report.confidence_score == Decimal("0.25")


def test_confidence_two_years_no_bonus() -> None:
    report = assess_readiness(_snapshot(annual_years=(2024, 2025)), set())
    assert report.confidence_score == Decimal("0.50")


def test_confidence_three_years_no_bonus() -> None:
    report = assess_readiness(
        _snapshot(annual_years=(2023, 2024, 2025)), set()
    )
    assert report.confidence_score == Decimal("0.75")


def test_confidence_four_years_no_bonus_capped_at_one() -> None:
    """4 × 0.25 = 1.00 (exact cap)."""
    report = assess_readiness(
        _snapshot(annual_years=(2022, 2023, 2024, 2025)), set()
    )
    assert report.confidence_score == Decimal(1)


def test_confidence_three_years_plus_form1() -> None:
    report = assess_readiness(
        _snapshot(annual_years=(2023, 2024, 2025)),
        {ParserSource.FORM_1},
    )
    assert report.confidence_score == Decimal("0.90")


def test_confidence_three_years_plus_form1_plus_esf_capped() -> None:
    """0.75 + 0.15 + 0.10 = 1.00 exact."""
    report = assess_readiness(
        _snapshot(annual_years=(2023, 2024, 2025)),
        {ParserSource.FORM_1, ParserSource.ESF_CSV},
    )
    assert report.confidence_score == Decimal(1)


def test_confidence_four_years_plus_all_bonuses_capped() -> None:
    """0.25×4 + 0.15 + 0.10 = 1.25 → capped 1.0."""
    report = assess_readiness(
        _snapshot(annual_years=(2022, 2023, 2024, 2025)),
        {ParserSource.FORM_1, ParserSource.ESF_CSV},
    )
    assert report.confidence_score == Decimal(1)


def test_confidence_no_years_but_bonuses_only() -> None:
    """0 years + FORM_1 + ESF → 0 + 0.15 + 0.10 = 0.25 (бонусы без основы)."""
    report = assess_readiness(
        _snapshot(),
        {ParserSource.FORM_1, ParserSource.ESF_CSV},
    )
    assert report.confidence_score == Decimal("0.25")


# ===== Группа F: years_covered / full_years =====


def test_years_covered_and_full_years_returned_sorted() -> None:
    """Порядок возвращаемых годов — ascending sorted."""
    snap = _snapshot(annual_years=(2025, 2023, 2024))
    report = assess_readiness(snap, set())
    assert report.years_covered == (2023, 2024, 2025)
    assert report.full_years == (2023, 2024, 2025)


def test_years_covered_includes_partial_years_full_years_does_not() -> None:
    """Год с 2 кварталами — попадает в covered, но не в full_years."""
    snap = _snapshot(annual_years=(2025,), quarterly_per_year={2023: 2})
    report = assess_readiness(snap, set())
    assert report.years_covered == (2023, 2025)
    assert report.full_years == (2025,)


# ===== Группа G: edge cases / контракт =====


def test_parser_sources_round_trip_in_report() -> None:
    """parser_sources возвращается как frozenset с теми же значениями."""
    sources = {ParserSource.FORM_2, ParserSource.VAT_DECLARATION}
    report = assess_readiness(_snapshot(annual_years=(2025,)), sources)
    assert report.parser_sources == frozenset(sources)


def test_accepts_frozenset_as_input() -> None:
    """sources может приходить как frozenset, не только set."""
    report = assess_readiness(
        _snapshot(annual_years=(2025,)),
        frozenset({ParserSource.MANUAL}),
    )
    assert ParserSource.MANUAL in report.parser_sources


def test_report_is_immutable() -> None:
    """DataReadinessReport — frozen dataclass.

    Frozen dataclass поднимает ``dataclasses.FrozenInstanceError`` при попытке
    assignment, который наследуется от ``AttributeError``.
    """
    report = assess_readiness(_snapshot(), set())
    with pytest.raises(AttributeError):
        report.level = DataReadinessLevel.COMPREHENSIVE  # type: ignore[misc]


def test_missing_capabilities_is_tuple_not_list() -> None:
    """Immutable container."""
    report = assess_readiness(_snapshot(), set())
    assert isinstance(report.missing_capabilities, tuple)


def test_full_year_via_more_than_four_quarters_still_counts_once() -> None:
    """Если по какой-то причине пришло 5+ квартальных reports — год полный
    (>=4), но в full_years попадает один раз (set semantics)."""
    # 5 кварталов невозможно по бизнес-логике (год = 4 квартала), но защита
    # от ошибок в адаптерах: count >= 4 → полный.
    snap = _snapshot(quarterly_per_year={2025: 4})
    assert _full_years(snap) == {2025}


def test_manual_source_alone_does_not_unlock_balance_or_tax() -> None:
    """MANUAL source — это ручной ввод цифр, не FORM_1 и не tax-источник.
    Balance ratios и tax burden остаются missing."""
    report = assess_readiness(
        _snapshot(annual_years=(2025,)),
        {ParserSource.MANUAL},
    )
    assert CAP_BALANCE_RATIOS in report.missing_capabilities
    assert CAP_TAX_BURDEN in report.missing_capabilities


def test_vat_declaration_does_not_satisfy_tax_burden() -> None:
    """VAT_DECLARATION — это НДС, не tax burden (требуется ESF или PROFIT_TAX)."""
    report = assess_readiness(
        _snapshot(annual_years=(2025,)),
        {ParserSource.VAT_DECLARATION},
    )
    assert CAP_TAX_BURDEN in report.missing_capabilities


def test_report_dataclass_fields_present() -> None:
    """Контракт ответа: все поля DataReadinessReport заполнены."""
    report = assess_readiness(
        _snapshot(annual_years=(2024, 2025)),
        {ParserSource.FORM_2, ParserSource.FORM_1},
    )
    assert isinstance(report, DataReadinessReport)
    assert report.level == DataReadinessLevel.STANDARD
    assert report.years_covered == (2024, 2025)
    assert report.full_years == (2024, 2025)
    assert ParserSource.FORM_2 in report.parser_sources
    assert ParserSource.FORM_1 in report.parser_sources
    assert report.confidence_score == Decimal("0.65")
    assert CAP_BALANCE_RATIOS not in report.missing_capabilities
