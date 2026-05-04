"""Pydantic-схемы для bank/borrowers/search и bank/dossiers."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchCardMonthlyPoint(_StrictModel):
    """Одна точка sparkline-чарта «Выручка 12 мес» в результате поиска.

    ``month`` — ISO YYYY-MM; ``revenue`` — Decimal как str (UZS sum).
    """

    month: str
    revenue: str


class SearchCardData(_StrictModel):
    """Расширенные данные result-card: заполняются только когда у заёмщика есть
    bank-mode досье (``BorrowerSearchResponse.dossier_id`` не None). UI рисует
    ScoreRing + mini-meta + RevenueSparkline по этим полям.
    """

    legal_form: str  # "llc" / "pe" / "jsc" / ...
    recommendation: Literal["approve", "review", "reject"]
    revenue_ltm: str | None  # Decimal как str (UZS sum); None если KPI null
    yoy_pct: float | None
    business_age_months: int | None
    signals_total: int  # len(red_flags) — сработавшие
    signals_evaluated: int  # rules_evaluated — всего проверено правил
    monthly_revenue_12m: list[SearchCardMonthlyPoint]


class BorrowerSearchResponse(_StrictModel):
    """Результат поиска по ИНН. UI разводит на 3 ветки:

    * ``found=False`` → загрузить выгрузки для нового заёмщика
    * ``found=True``, ``dossier_id=None`` → загрузить выгрузки для существующего
    * ``found=True``, ``dossier_id`` есть → открыть существующее досье

    Когда есть досье, дополнительно отдаём ``card`` для богатой result-карточки
    (revenue sparkline + KPI mini-meta + recommendation pill). Без отдельного
    round-trip на ``/api/dossier/{id}``.
    """

    found: bool
    borrower_name: str | None = None
    dossier_id: UUID | None = None
    score: int | None = None
    display_score: int | None = None
    created_at: datetime | None = None
    card: SearchCardData | None = None


class BankDossierListItemResponse(_StrictModel):
    """Строка истории. ``borrower_inn_masked`` — `XXXXX1234` per Security Hard Rules."""

    dossier_id: UUID
    borrower_inn_masked: str
    borrower_name: str
    score: int
    display_score: int
    recommendation: str
    created_at: datetime
    analyst_id: UUID | None = None
    analyst_full_name: str | None = None


class BankDossierListResponse(_StrictModel):
    items: list[BankDossierListItemResponse]
    total: int
    page: int
    page_size: int


# Query-param literal: только два значения, чтобы FastAPI/OpenAPI отображали
# валидные опции.
ListFilter = Literal["mine", "all"]


class ListQueryParams(_StrictModel):
    """Декларативные query params (используется FastAPI через ``Depends``)."""

    filter: ListFilter = "all"
    q: str | None = Field(default=None, max_length=255)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
