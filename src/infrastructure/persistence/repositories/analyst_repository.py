"""SqlAlchemyAnalystRepository: lookup и сохранение seeded банковских аналитиков.

Read-методы возвращают DTO ``AnalystIdentity`` (без password_hash).
``get_by_email_with_hash`` отдаёт ORM-объект и используется только из
AuthnAdapter в момент проверки пароля — ORM не уходит выше application.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.analyst_identity import AnalystIdentity
from infrastructure.persistence.mappers.analyst_mapper import analyst_from_orm
from infrastructure.persistence.models.analyst import AnalystORM


class SqlAlchemyAnalystRepository:
    """CRUD-ограниченный (без delete) репозиторий аналитиков."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str,
        role: str = "analyst",
        is_active: bool = True,
    ) -> UUID:
        orm = AnalystORM(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_active=is_active,
        )
        self._session.add(orm)
        await self._session.flush()
        return orm.id

    async def get_by_id(self, analyst_id: UUID) -> AnalystIdentity | None:
        orm = await self._session.get(AnalystORM, analyst_id)
        return analyst_from_orm(orm) if orm is not None else None

    async def get_by_email(self, email: str) -> AnalystIdentity | None:
        stmt = select(AnalystORM).where(AnalystORM.email == email)
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return analyst_from_orm(orm) if orm is not None else None

    async def get_by_email_with_hash(self, email: str) -> AnalystORM | None:
        """Только для AuthnAdapter: нужен password_hash для verify().

        Возвращает ORM-инстанс намеренно — DTO не должен нести credentials.
        Вызывающий обязан не пропускать ORM выше своего модуля.
        """
        stmt = select(AnalystORM).where(AnalystORM.email == email)
        return (await self._session.execute(stmt)).scalar_one_or_none()
