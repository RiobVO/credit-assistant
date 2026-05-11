"""Data Readiness Assessment — оценка достаточности данных для скоринга.

Pure-функция ``assess_readiness`` получает ``BorrowerSnapshot`` и множество
парсер-источников (``ParserSource``), возвращает ``DataReadinessReport`` с
уровнем готовности, списком покрытых лет, отсутствующими способностями
анализа и confidence_score.

См. ADR 0010 — обоснование 4-уровневой шкалы и формулы.

Контракт:
- Domain pure: никаких I/O, никаких side-effects, никаких dependency на
  infrastructure/application слои. Только snapshot и enum-set на вход.
- «Полный год» = annual report за этот календарный год (annual_reports)
  ИЛИ ≥4 квартальных reports за тот же year (quarterly_reports).
- COMPREHENSIVE требует **3 года подряд** (consecutive) + FORM_1 в sources
  + хотя бы один tax-источник (ESF_CSV или PROFIT_TAX).
- Capabilities derive независимо от level: yoy_trend от ≥2 consecutive,
  cagr от ≥3 consecutive, balance_ratios от FORM_1, tax_burden от
  ESF_CSV/PROFIT_TAX. Level — сводная метрика над тем же набором.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from itertools import pairwise

from domain.entities.borrower_snapshot import BorrowerSnapshot


class DataReadinessLevel(StrEnum):
    INSUFFICIENT = "insufficient"
    MINIMAL = "minimal"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"


class ParserSource(StrEnum):
    """Парсер-источник, через который данные попали в snapshot.

    ``MANUAL`` — ручной ввод в Шаге 2/3 (без backend-парсера); ``FORM_2`` —
    Отчёт о финансовых результатах; ``FORM_1`` — Бухбаланс; остальные —
    одноимённые форматы выгрузок my3.soliq.uz / ЭСФ-портал.
    """

    FORM_2 = "form_2"
    FORM_1 = "form_1"
    VAT_DECLARATION = "vat_declaration"
    ESF_CSV = "esf_csv"
    PROFIT_TAX = "profit_tax"
    MANUAL = "manual"


# Capability identifiers — стабильные строки для downstream UI/PDF.
CAP_YOY_TREND = "yoy_trend"
CAP_CAGR = "cagr"
CAP_BALANCE_RATIOS = "balance_ratios"
CAP_TAX_BURDEN = "tax_burden"


@dataclass(frozen=True, slots=True)
class DataReadinessReport:
    """Отчёт о готовности данных для скоринга.

    Все коллекции — immutable (frozen dataclass + tuple/frozenset). Pydantic
    в interfaces слое сериализует их в JSON lists.

    ``years_covered`` — все годы с любыми данными (annual ИЛИ хотя бы один
    квартал). ``full_years`` — годы с полным покрытием. Различение полезно
    для UI: «2023, 2024, 2025 (полные: 2024, 2025)».
    """

    level: DataReadinessLevel
    years_covered: tuple[int, ...]
    full_years: tuple[int, ...]
    missing_capabilities: tuple[str, ...]
    parser_sources: frozenset[ParserSource]
    confidence_score: Decimal


def assess_readiness(
    snapshot: BorrowerSnapshot,
    sources: set[ParserSource] | frozenset[ParserSource],
) -> DataReadinessReport:
    """Оценить готовность данных snapshot для скоринга.

    Pure. ``sources`` — набор парсеров, которые внесли данные в snapshot
    (приходит от application слоя по prefix-keys из source_trail).
    """
    sources_frozen = frozenset(sources)

    full_years = _full_years(snapshot)
    any_years = _any_years(snapshot)
    consecutive_max = _max_consecutive_run(full_years)

    has_form1 = ParserSource.FORM_1 in sources_frozen
    has_tax_source = (
        ParserSource.ESF_CSV in sources_frozen
        or ParserSource.PROFIT_TAX in sources_frozen
    )

    level = _classify_level(consecutive_max, has_form1, has_tax_source)
    missing = _missing_capabilities(consecutive_max, has_form1, has_tax_source)
    score = _confidence_score(len(full_years), has_form1, has_tax_source)

    return DataReadinessReport(
        level=level,
        years_covered=tuple(sorted(any_years)),
        full_years=tuple(sorted(full_years)),
        missing_capabilities=tuple(missing),
        parser_sources=sources_frozen,
        confidence_score=score,
    )


def _classify_level(
    consecutive_max: int,
    has_form1: bool,
    has_tax_source: bool,
) -> DataReadinessLevel:
    """4-уровневая шкала — высший достигнутый уровень.

    COMPREHENSIVE требует одновременно: 3+ лет consecutive, FORM_1
    (balance ratios), хотя бы один tax-источник (ESF или PROFIT_TAX).
    """
    if consecutive_max >= 3 and has_form1 and has_tax_source:
        return DataReadinessLevel.COMPREHENSIVE
    if consecutive_max >= 2:
        return DataReadinessLevel.STANDARD
    if consecutive_max >= 1:
        return DataReadinessLevel.MINIMAL
    return DataReadinessLevel.INSUFFICIENT


def _missing_capabilities(
    consecutive_max: int,
    has_form1: bool,
    has_tax_source: bool,
) -> list[str]:
    """Что НЕ доступно при текущем составе данных.

    Derive независимо от level — capabilities привязаны к конкретным
    данным (consecutive years × tax source × balance source), не к
    сводной шкале.
    """
    missing: list[str] = []
    if consecutive_max < 2:
        missing.append(CAP_YOY_TREND)
    if consecutive_max < 3:
        missing.append(CAP_CAGR)
    if not has_form1:
        missing.append(CAP_BALANCE_RATIOS)
    if not has_tax_source:
        missing.append(CAP_TAX_BURDEN)
    return missing


def _confidence_score(
    n_full_years: int,
    has_form1: bool,
    has_tax_source: bool,
) -> Decimal:
    """Confidence ∈ [0, 1]: 0.25 за каждый полный год + 0.15 за FORM_1
    + 0.10 за tax-источник, cap на 1.0.

    Cap нужен потому что 4 полных года × 0.25 = 1.0 без bonus'ов, а с
    bonus'ами уйдёт за 1.0.
    """
    score = (
        Decimal("0.25") * n_full_years
        + (Decimal("0.15") if has_form1 else Decimal(0))
        + (Decimal("0.10") if has_tax_source else Decimal(0))
    )
    return min(score, Decimal(1))


def _full_years(snapshot: BorrowerSnapshot) -> set[int]:
    """Годы с полным покрытием: annual report ИЛИ ≥4 квартальных за year."""
    full: set[int] = set()
    for report in snapshot.annual_reports:
        full.add(report.period.end.year)

    quarterly_count_by_year: dict[int, int] = {}
    for report in snapshot.quarterly_reports:
        year = report.period.end.year
        quarterly_count_by_year[year] = quarterly_count_by_year.get(year, 0) + 1
    for year, count in quarterly_count_by_year.items():
        if count >= 4:
            full.add(year)
    return full


def _any_years(snapshot: BorrowerSnapshot) -> set[int]:
    """Все годы с любыми данными (annual или хотя бы один квартал)."""
    years: set[int] = set()
    for report in snapshot.annual_reports:
        years.add(report.period.end.year)
    for report in snapshot.quarterly_reports:
        years.add(report.period.end.year)
    return years


def _max_consecutive_run(years: set[int]) -> int:
    """Максимальная длина непрерывной серии лет в наборе.

    {} → 0, {2024} → 1, {2024, 2025} → 2, {2023, 2025} → 1 (gap),
    {2023, 2024, 2025} → 3, {2022, 2024, 2025} → 2.
    """
    if not years:
        return 0
    sorted_years = sorted(years)
    max_run = 1
    current = 1
    for prev, curr in pairwise(sorted_years):
        if curr - prev == 1:
            current += 1
            if current > max_run:
                max_run = current
        else:
            current = 1
    return max_run
