"""OkedBenchmarkBucket DTO: запись каталога отраслевых медиан по UZ-ОКЭД.

ADR-0024 / Commit 3: catalog mirror для observations_builder ROE-benchmark
строки. Источник — ``config/benchmarks/oked-uz.json``. Loader живёт в
``infrastructure.catalog.oked_benchmark`` — этот модуль pure dataclass.

Каждый bucket покрывает одну ОКЭД-секцию (A/C/F/G/H/I/J). Lookup по
section-letter, либо по 2-digit prefix из ``oked_subsections``. Для borrower'а
с ОКЭД 43.39 (Отделочные работы → раздел 43 → секция F) bucket возвращает
``code_prefix="F"``, ``name_ru="Строительство"``.

UZ-specific median **не публикуется stat.uz / ЦБ РУз / CERR** в открытом
виде. Все числовые поля могут быть ``None`` — это явная политика «честно null,
не выдумывать число». Заполняется по мере появления commission-исследований
(CERR / KPMG / Stat.uz микроданные).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OkedBenchmarkMedian:
    """Медианные финпоказатели per-bucket. None = UZ-данных нет (не fake)."""

    roe_pct: float | None
    net_margin_pct: float | None
    asset_turnover: float | None
    debt_to_equity: float | None


@dataclass(frozen=True, slots=True)
class OkedBenchmarkBucket:
    """Одна отраслевая секция UZ-ОКЭД."""

    code_prefix: str  # "A" / "C" / "F" / "G" / "H" / "I" / "J"
    oked_subsections: tuple[str, ...]  # ("41", "42", "43") для F
    name_ru: str
    name_uz: str
    median: OkedBenchmarkMedian
    sample_size: int | None
    source: str
    notes: str
