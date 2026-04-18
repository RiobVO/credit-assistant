"""SqlAlchemyBorrowerSnapshotRepository: insert-only, чтение с join borrower."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.borrower_snapshot import BorrowerSnapshot
from infrastructure.persistence.mappers.borrower_mapper import borrower_from_orm
from infrastructure.persistence.mappers.snapshot_mapper import (
    snapshot_from_payload,
    snapshot_to_payload,
)
from infrastructure.persistence.models.borrower import BorrowerORM
from infrastructure.persistence.models.borrower_snapshot import BorrowerSnapshotORM


class SqlAlchemyBorrowerSnapshotRepository:
    """Реализация ``BorrowerSnapshotRepositoryPort``. Snapshot иммутабелен — только save/get."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, snapshot: BorrowerSnapshot, borrower_id: UUID) -> UUID:
        new_id = uuid4()
        orm = BorrowerSnapshotORM(
            id=new_id,
            borrower_id=borrower_id,
            as_of=snapshot.as_of,
            payload=snapshot_to_payload(snapshot),
        )
        self._session.add(orm)
        await self._session.flush()
        return new_id

    async def get_by_id(self, snapshot_id: UUID) -> BorrowerSnapshot | None:
        # Один запрос с join: tuple (snapshot_orm, borrower_orm).
        stmt = (
            select(BorrowerSnapshotORM, BorrowerORM)
            .join(BorrowerORM, BorrowerSnapshotORM.borrower_id == BorrowerORM.id)
            .where(BorrowerSnapshotORM.id == snapshot_id)
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        snapshot_orm, borrower_orm = row
        borrower = borrower_from_orm(borrower_orm)
        return snapshot_from_payload(snapshot_orm.payload, borrower)
