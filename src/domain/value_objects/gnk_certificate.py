"""GnkCertificate: справка из ГНК для подтверждения статуса плательщика НДС.

Phase A (T0.3) — manual upload справки аналитиком (PDF/JPG). Phase B (CA-DS28) —
public lookup на soliq.uz/services/search/ + automatic fetch. Source-enum
расширяемый: ``uploaded`` для Phase A, ``gnk_live`` / ``gnk_cached`` /
``fallback`` зарезервированы под Phase B (mirror UsdUzsRate / ADR-0014).

Domain value object — immutable, validated at construction (через INN).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from domain.value_objects.inn import INN

GnkSource = Literal["uploaded", "gnk_live", "gnk_cached", "fallback"]
GnkStatus = Literal["active", "suspended", "revoked", "unknown"]


@dataclass(frozen=True, slots=True)
class GnkCertificate:
    """Состояние плательщика НДС по данным ГНК.

    Phase A invariants:
    - ``source == "uploaded"`` → ``uploaded_at`` и ``uploaded_by_analyst_id`` обязательны,
      ``file_id`` указывает на binary в gnk_certificates table.
    - ``cert_id`` опционален (Soliq внутренний номер; для manual upload может
      отсутствовать — аналитик не всегда видит cert_id в выгрузке).
    - ``okveds`` нормализован (без дубликатов, сорт. по убыванию приоритета —
      первый = основной).
    """

    borrower_inn: INN
    full_name: str
    status: GnkStatus
    okveds: list[str] = field(default_factory=list)
    source: GnkSource = "uploaded"
    cert_id: str | None = None
    uploaded_at: datetime | None = None
    uploaded_by_analyst_id: UUID | None = None
    file_id: UUID | None = None
