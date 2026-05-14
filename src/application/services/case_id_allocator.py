"""SqlAlchemyCaseIdAllocator: monotonic case_id с year-rollover.

Алгоритм (внутри текущей транзакции):

1. ``pg_advisory_xact_lock(year)`` — сериализует конкурентные аллокации
   для одного года; lock освобождается на commit/rollback, ничего
   вручную чистить не нужно.
2. Читает ``MAX(year)`` из всех существующих case_id через
   ``SUBSTRING(case_id FROM 4 FOR 4)``. Если ``now.year`` строго больше —
   делает ``ALTER SEQUENCE ... RESTART WITH 1`` (year boundary).
   Если max_year=NULL (пустая таблица) — sequence НЕ трогаем: миграция
   уже синхронизировала её на правильный setval. Reset только при
   реальной смене года.
3. ``SELECT nextval('dossier_case_seq')`` — atomic.
4. Форматирует ``BR-{year}-{seq:04d}``.

Trade-off: same-year writes сериализуются (один advisory lock на год).
Для bank-internal tool с <10 досье/час это незаметно. Альтернатива
(counter table + UPSERT RETURNING) проще, но roadmap T1.1 зафиксировал
sequence-подход — оставляем.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SqlAlchemyCaseIdAllocator:
    """Реализация ``CaseIdAllocatorPort`` поверх Postgres SEQUENCE + advisory lock."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def allocate(self, now: datetime) -> str:
        year = now.year

        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:k)"), {"k": year}
        )

        max_year_row = await self._session.execute(
            text("SELECT MAX(SUBSTRING(case_id FROM 4 FOR 4)::int) FROM dossiers")
        )
        max_year: int | None = max_year_row.scalar_one_or_none()

        if max_year is not None and year > max_year:
            await self._session.execute(
                text("ALTER SEQUENCE dossier_case_seq RESTART WITH 1")
            )

        seq_row = await self._session.execute(
            text("SELECT nextval('dossier_case_seq')")
        )
        seq: int = seq_row.scalar_one()
        return f"BR-{year}-{seq:04d}"
