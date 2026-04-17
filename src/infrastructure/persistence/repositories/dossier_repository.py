"""SqlAlchemyDossierRepository: insert-only результат прогона правил."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.dossier_record import DossierRecord
from infrastructure.persistence.mappers.dossier_mapper import (
    dossier_record_from_orm_columns,
    red_flags_to_jsonb,
)
from infrastructure.persistence.models.dossier import DossierORM


class SqlAlchemyDossierRepository:
    """Реализация ``DossierRepositoryPort``. Досье иммутабельно — только save/get."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: DossierRecord, snapshot_id: UUID) -> UUID:
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
