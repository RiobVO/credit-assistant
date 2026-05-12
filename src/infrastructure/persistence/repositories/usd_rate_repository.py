"""SqlAlchemyUsdRateRepository: DB-cached USD/UZS courses (T0.2).

Адаптер для usd_uzs_rates table. Используется UsdRateService как primary
store: «есть today's row → отдай; нет → fetch CBU → save → отдай; CBU down →
get_latest fallback».

``save`` использует ``ON CONFLICT (date) DO NOTHING`` — конкурентные writes
из двух параллельных endpoint-calls безопасны: первый succeed, второй no-op
(потом get_for_date вернёт первого, оба requestа отдадут одинаковый rate).
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.exchange_rate import UsdUzsRate
from infrastructure.persistence.models.usd_uzs_rate import UsdUzsRateORM


class SqlAlchemyUsdRateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_date(self, target: date_type) -> UsdUzsRate | None:
        """Курс на конкретный календарный день. None если в БД нет."""
        orm = await self._session.get(UsdUzsRateORM, target)
        return _to_dto(orm) if orm is not None else None

    async def get_latest(self) -> UsdUzsRate | None:
        """Самый свежий курс (по убыванию date). None если БД пустая."""
        stmt = select(UsdUzsRateORM).order_by(UsdUzsRateORM.date.desc()).limit(1)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _to_dto(orm) if orm is not None else None

    async def save(
        self,
        *,
        rate: UsdUzsRate,
        raw_response: dict[str, Any] | None,
        fetched_at: datetime,
        nominal: int = 1,
    ) -> None:
        """Сохраняет курс. ON CONFLICT (date) DO NOTHING — конкурент-safe."""
        stmt = (
            insert(UsdUzsRateORM)
            .values(
                date=rate.asof,
                rate=rate.rate,
                nominal=nominal,
                source=rate.source,
                fetched_at=fetched_at,
                raw_response=raw_response,
            )
            .on_conflict_do_nothing(index_elements=["date"])
        )
        await self._session.execute(stmt)
        await self._session.flush()


def _to_dto(orm: UsdUzsRateORM) -> UsdUzsRate:
    """ORM → DTO. Numeric(14,4) уже Decimal — без конверсии."""
    return UsdUzsRate(
        rate=Decimal(orm.rate),
        asof=orm.date,
        source=orm.source,
    )
