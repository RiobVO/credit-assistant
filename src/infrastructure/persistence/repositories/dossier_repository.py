"""SqlAlchemyDossierRepository: insert-only результат прогона правил."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.dossier_record import DossierRecord
from application.dto.dossier_view_record import DossierViewRecord
from infrastructure.persistence.mappers.borrower_mapper import borrower_from_orm
from infrastructure.persistence.mappers.dossier_mapper import (
    dossier_record_from_orm_columns,
    red_flags_to_jsonb,
)
from infrastructure.persistence.mappers.snapshot_mapper import snapshot_from_payload
from infrastructure.persistence.models.borrower import BorrowerORM
from infrastructure.persistence.models.borrower_snapshot import BorrowerSnapshotORM
from infrastructure.persistence.models.dossier import DossierORM


class SqlAlchemyDossierRepository:
    """Реализация ``DossierRepositoryPort``. Досье иммутабельно — только save/get."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        record: DossierRecord,
        snapshot_id: UUID,
        *,
        source_mode: str = "accountant",
        created_by_analyst_id: UUID | None = None,
    ) -> UUID:
        new_id = uuid4()
        orm = DossierORM(
            id=new_id,
            snapshot_id=snapshot_id,
            score=record.score,
            recommendation=record.recommendation,
            severity_breakdown=dict(record.severity_breakdown),
            red_flags=red_flags_to_jsonb(record.red_flags),
            rules_version=record.rules_version,
            rules_evaluated=record.rules_evaluated,
            source_mode=source_mode,
            created_by_analyst_id=created_by_analyst_id,
        )
        self._session.add(orm)
        await self._session.flush()
        return new_id

    async def get_by_id(self, dossier_id: UUID) -> DossierRecord | None:
        orm = await self._session.get(DossierORM, dossier_id)
        if orm is None:
            return None
        return dossier_record_from_orm_columns(
            score=orm.score,
            recommendation=orm.recommendation,
            severity_breakdown=orm.severity_breakdown,
            red_flags=orm.red_flags,
            rules_version=orm.rules_version,
            rules_evaluated=orm.rules_evaluated,
        )

    async def get_view_by_id(self, dossier_id: UUID) -> DossierViewRecord | None:
        """Один SELECT с двумя JOIN: dossier + snapshot + borrower.

        Используется экраном /dossier/[id] (Phase 3.B). Альтернатива — три
        отдельных запроса через ``snapshot_repo.get_by_id`` и
        ``dossier_repo.get_by_id``; одиночный JOIN дешевле и атомарнее по
        чтению (snapshot не пропадёт между запросами благодаря FK RESTRICT,
        но один round-trip читается как одна операция).
        """
        stmt = (
            select(DossierORM, BorrowerSnapshotORM, BorrowerORM)
            .join(
                BorrowerSnapshotORM, DossierORM.snapshot_id == BorrowerSnapshotORM.id
            )
            .join(BorrowerORM, BorrowerSnapshotORM.borrower_id == BorrowerORM.id)
            .where(DossierORM.id == dossier_id)
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        dossier_orm, snapshot_orm, borrower_orm = row

        borrower = borrower_from_orm(borrower_orm)
        snapshot = snapshot_from_payload(snapshot_orm.payload, borrower)
        dossier_record = dossier_record_from_orm_columns(
            score=dossier_orm.score,
            recommendation=dossier_orm.recommendation,
            severity_breakdown=dossier_orm.severity_breakdown,
            red_flags=dossier_orm.red_flags,
            rules_version=dossier_orm.rules_version,
            rules_evaluated=dossier_orm.rules_evaluated,
        )
        return DossierViewRecord(
            dossier_id=dossier_orm.id,
            dossier=dossier_record,
            snapshot=snapshot,
            created_at=dossier_orm.created_at,
        )
