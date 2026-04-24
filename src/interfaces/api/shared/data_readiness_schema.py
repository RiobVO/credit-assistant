"""Pydantic-схемы POST /api/manual-input/readiness.

Stateless evaluation: фронт шлёт аналитический срез form state + source_trail
из CA-027 dropzone, бэк возвращает ``DataReadinessReport`` сериализованный.

Decimal → str (ADR-0007: JSON float теряет точность). Enum → str values.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataReadinessRequest(_StrictModel):
    """Аналитический срез form state Шага 2.

    Frontend derives эти списки из watched form values:
    - ``annual_report_years``: годы с непустым annual cell в revenue/netProfit
    - ``full_quarter_years``: годы с 4 заполненными квартальными cells
    - ``partial_quarter_years``: годы с ≥1 квартальной cell, но <4
    - ``source_trail``: память от parsed-files-dropzone (CA-027)

    Все списки могут быть пустыми (пустая форма → INSUFFICIENT).
    """

    annual_report_years: list[int] = Field(default_factory=list)
    full_quarter_years: list[int] = Field(default_factory=list)
    partial_quarter_years: list[int] = Field(default_factory=list)
    source_trail: dict[str, str] = Field(default_factory=dict)


class DataReadinessResponse(_StrictModel):
    """Сериализованный DataReadinessReport.

    ``level`` и ``parser_sources`` — string enum values
    (e.g. "insufficient"/"comprehensive", "form_1"/"esf_csv").
    ``confidence_score`` — Decimal как строка ("0.75").
    """

    level: str
    years_covered: list[int]
    full_years: list[int]
    missing_capabilities: list[str]
    parser_sources: list[str]
    confidence_score: str
