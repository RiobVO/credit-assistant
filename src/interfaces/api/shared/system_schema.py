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
