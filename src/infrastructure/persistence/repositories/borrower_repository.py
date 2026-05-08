"""SqlAlchemyBorrowerRepository: UPSERT по INN через postgres ON CONFLICT."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.borrower import Borrower
from domain.value_objects.inn import INN
from infrastructure.persistence.mappers.borrower_mapper import (
    borrower_from_orm,
    borrower_to_orm_kwargs,
)
from infrastructure.persistence.models.borrower import BorrowerORM


class SqlAlchemyBorrowerRepository:
    """Реализация ``BorrowerRepositoryPort`` поверх ``AsyncSession``.

    UPSERT по уникальному INN. Если запись уже есть — обновляются все поля,
    кроме id и created_at. Это атомарно, без race condition при параллельных
    прогонах одного и того же ИНН.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, borrower: Borrower) -> UUID:
        values = borrower_to_orm_kwargs(borrower)
        new_id = uuid4()
        insert_stmt = pg_insert(BorrowerORM).values(id=new_id, **values)
        update_set = {k: insert_stmt.excluded[k] for k in values}
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[BorrowerORM.inn],
            set_=update_set,
        ).returning(BorrowerORM.id)
        result = await self._session.execute(upsert_stmt)
        await self._session.flush()
        returned: UUID = result.scalar_one()
        return returned

    async def get_by_inn(self, inn: INN) -> Borrower | None:
        stmt = select(BorrowerORM).where(BorrowerORM.inn == inn.value)
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return borrower_from_orm(orm) if orm is not None else None

    async def get_by_id(self, borrower_id: UUID) -> Borrower | None:
        orm = await self._session.get(BorrowerORM, borrower_id)
        return borrower_from_orm(orm) if orm is not None else None
