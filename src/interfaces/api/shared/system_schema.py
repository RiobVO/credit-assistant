"""Pydantic-схемы для system-health endpoints."""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    # ``key`` — стабильный идентификатор (frontend маппит на i18n + иконку).
    # ``status`` — ``ok | degraded | down | not_implemented``.
    key: str
    status: str
    # ``tip`` — plain-language подсказка, что делать аналитику если не-ok.
    # Опционально: для ok-сервисов отсутствует.
    tip: str | None = None


class SystemHealthResponse(BaseModel):
    # Overall status: worst-of всех сервисов (ok < degraded < down).
    # not_implemented сервисы не влияют на overall — это не сбой, это нет фичи.
    status: str
    checked_at: datetime
    services: list[ServiceStatus]


class UptimeDayItem(BaseModel):
    day: date_type
    status: str


class UptimeHistoryResponse(BaseModel):
    # ``first_seen_day`` — день первой записи в БД (момент production-deploy).
    # ``days`` — массив только реально-известных дней. Frontend сам достраивает
    # «до запуска» серые квадраты.
    first_seen_day: date_type | None
    days: list[UptimeDayItem]


class OkvedItem(BaseModel):
    # CA-DS17: одна запись OKVED catalog. ``short_*``/``full_*`` — для compact
    # vs detailed display. Frontend выбирает локаль (next-intl), сейчас
    # использует ``full_ru``/``full_uz`` в autocomplete и ``short_*`` в chip.
    code: str
    short_ru: str
    full_ru: str
    short_uz: str
    full_uz: str


class OkvedCatalogResponse(BaseModel):
    # CA-DS17: список МСБ OKVED-кодов из ``config/okved/uz_msb.json``.
    # Sorted by ``code`` ascending для стабильного UI rendering.
    items: list[OkvedItem]


class UsdRateResponse(BaseModel):
    # CA-DS24: USD/UZS rate для UI-конвертации в loan-wizard.
    # ``rate`` строкой — сохраняем Decimal-точность через JSON wire.
    # ``source`` ∈ {manual, env, cbu (CA-DS24b)} — UI может показать badge.
    rate: str
    asof: date_type
    source: str
