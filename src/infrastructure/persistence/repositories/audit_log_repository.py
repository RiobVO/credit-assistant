"""SqlAlchemyAuditLogRepository: append-only insert + чтение для отчётов.

API намеренно минимальное: запись и листинг по аналитику. Mutations
(update/delete) не предусмотрены — это безопасностный инвариант
(см. Security Hard Rules в CLAUDE.md).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.audit_log import AuditLogORM


class SqlAlchemyAuditLogRepository:
    def __init__(self, session: AsyncSession, brand_id: str = "default") -> None:
        """T1.4 (ADR-0018): ``brand_id`` привязывается к repo-инстансу.

        Все `.record(...)` calls этой инстанции пишут одинаковый brand_id —
        тот, что текущая инсталляция держит в ``Settings.brand_id``. Default
        ``"default"`` оставлен для тестов и Phase 4 legacy callsite'ов,
        которые ещё не пробрасывают settings.
        """
        self._session = session
        self._brand_id = brand_id

    async def record(
        self,
        *,
        event: str,
        analyst_id: UUID | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> UUID:
        # T3.2: request_id вытаскивается из ``structlog.contextvars`` (его
        # туда положил ``RequestIDMiddleware``). Best-effort: записи аудита
        # из CLI/jobs/background-tasks без middleware остаются с NULL —
        # это валидно по schema.
        request_id = structlog.contextvars.get_contextvars().get("request_id")

        orm = AuditLogORM(
            analyst_id=analyst_id,
            event=event,
            target_type=target_type,
            target_id=target_id,
            payload=payload or {},
            brand_id=self._brand_id,
            request_id=request_id if isinstance(request_id, str) else None,
        )
        self._session.add(orm)
        await self._session.flush()
        return orm.id

    async def list_by_analyst(
        self, analyst_id: UUID, *, limit: int = 100
    ) -> list[AuditLogORM]:
        stmt = (
            select(AuditLogORM)
            .where(AuditLogORM.analyst_id == analyst_id)
            .order_by(desc(AuditLogORM.created_at))
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars())

    async def export_range(
        self,
        *,
        from_: datetime,
        to: datetime,
        event: str | None = None,
    ) -> list[AuditLogORM]:
        """T3.5: список записей audit-лога для CSV-экспорта.

        Полу-открытый интервал ``[from_, to)``. Фильтр ``event`` —
        опциональный exact match. brand_id-инвариант обеспечивается
        конструктором: экспорт всегда отдаёт записи **текущей** инсталляции.

        Возвращаем list для simplicity (audit-объёмы pre-demo ≤ 100K rows
        не требуют streaming на repo-уровне — endpoint stream'ит CSV-байты,
        не строки БД). При росте объёмов мигрировать на
        ``stream_scalars()``.
        """
        from sqlalchemy import asc

        stmt = (
            select(AuditLogORM)
            .where(AuditLogORM.brand_id == self._brand_id)
            .where(AuditLogORM.created_at >= from_)
            .where(AuditLogORM.created_at < to)
            .order_by(asc(AuditLogORM.created_at))
        )
        if event is not None:
            stmt = stmt.where(AuditLogORM.event == event)
        return list((await self._session.execute(stmt)).scalars())
