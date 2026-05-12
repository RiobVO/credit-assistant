"""ORM для usd_uzs_rates: daily-granularity store для USD/UZS курса из CBU API.

PK = date — один курс на банковский день. Save via ``ON CONFLICT (date) DO
NOTHING`` для конкурент-safe writes из service-слоя.

``source`` — ``cbu_live | env | manual | db_cached | fallback`` (см.
``UsdUzsRate.source`` literal в DTO).

``raw_response`` — JSONB c оригинальным CBU JSON для аудита.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.database import Base


class UsdUzsRateORM(Base):
    __tablename__ = "usd_uzs_rates"

    date: Mapped[date_type] = mapped_column(Date, primary_key=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    nominal: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
