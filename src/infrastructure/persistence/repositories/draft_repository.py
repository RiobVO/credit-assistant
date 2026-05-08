"""SqlAlchemyDraftRepository: CRUD черновиков формы с TTL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from infrastructure.persistence.models.draft import DraftORM


class SqlAlchemyDraftRepository:
    """Реализация ``DraftRepositoryPort``. ``expires_at`` ставится в коде —
    server-side trigger не нужен, TTL и так управляется конфигом приложения.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _new_expiry(self) -> datetime:
        return datetime.now(UTC) + timedelta(days=get_settings().draft_ttl_days)

    async def create(self, payload: dict[str, Any]) -> UUID:
        new_id = uuid4()
        orm = DraftORM(id=new_id, payload=payload, expires_at=self._new_expiry())
        self._session.add(orm)
        await self._session.flush()
        return new_id

    async def update(self, draft_id: UUID, payload: dict[str, Any]) -> bool:
        orm = await self._session.get(DraftORM, draft_id)
        if orm is None:
            return False
        orm.payload = payload
        orm.expires_at = self._new_expiry()
        await self._session.flush()
        return True

    async def get(self, draft_id: UUID) -> dict[str, Any] | None:
        # Пропускаем истёкшие — auth по UUID, но истечение это политика приложения.
        stmt = select(DraftORM).where(
            DraftORM.id == draft_id,
            DraftORM.expires_at > datetime.now(UTC),
        )
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return dict(orm.payload) if orm is not None else None

    async def purge_expired(self) -> int:
        stmt = delete(DraftORM).where(DraftORM.expires_at <= datetime.now(UTC))
        # DELETE через AsyncSession возвращает CursorResult в рантайме;
        # тип-аннотация Result[Any] прячет .rowcount — приходится cast'ить.
        result = cast(CursorResult[Any], await self._session.execute(stmt))
        await self._session.flush()
        return result.rowcount or 0
