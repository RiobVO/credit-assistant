"""Integration: новые колонки dossier — source_mode + created_by_analyst_id."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.dossier_record import DossierRecord
from infrastructure.persistence.models.dossier import DossierORM
from infrastructure.persistence.repositories.analyst_repository import (
    SqlAlchemyAnalystRepository,
)
from infrastructure.persistence.repositories.borrower_repository import (
    SqlAlchemyBorrowerRepository,
)
from infrastructure.persistence.repositories.borrower_snapshot_repository import (
    SqlAlchemyBorrowerSnapshotRepository,
)
from infrastructure.persistence.repositories.dossier_repository import (
    SqlAlchemyDossierRepository,
)
from tests.fixtures.synthetic_borrowers import clean_borrower

pytestmark = pytest.mark.integration


def _record() -> DossierRecord:
    return DossierRecord(
        score=10,
        recommendation="approve",
        severity_breakdown={"low": 1},
        red_flags=(),
        rules_version="v1",
        rules_evaluated=17,
    )


async def test_save_defaults_to_accountant_mode(pg_session: AsyncSession) -> None:
    """Backward compat: callers без новых kwargs продолжают писать как accountant."""
    snapshot = clean_borrower()
    borrower_repo = SqlAlchemyBorrowerRepository(pg_session)
    snapshot_repo = SqlAlchemyBorrowerSnapshotRepository(pg_session)
    dossier_repo = SqlAlchemyDossierRepository(pg_session)

    borrower_id = await borrower_repo.upsert(snapshot.borrower)
    snapshot_id = await snapshot_repo.save(snapshot, borrower_id)
    dossier_id = await dossier_repo.save(_record(), snapshot_id, "BR-2026-B001")

    orm = await pg_session.get(DossierORM, dossier_id)
    assert orm is not None
    assert orm.source_mode == "accountant"
    assert orm.created_by_analyst_id is None


async def test_save_bank_mode_with_analyst(pg_session: AsyncSession) -> None:
    snapshot = clean_borrower()
    borrower_repo = SqlAlchemyBorrowerRepository(pg_session)
    snapshot_repo = SqlAlchemyBorrowerSnapshotRepository(pg_session)
    dossier_repo = SqlAlchemyDossierRepository(pg_session)
    analyst_repo = SqlAlchemyAnalystRepository(pg_session)

    analyst_id = await analyst_repo.add(
        email="bank@bank.uz", password_hash="$2b$12$x", full_name="Bank A"
    )
    borrower_id = await borrower_repo.upsert(snapshot.borrower)
    snapshot_id = await snapshot_repo.save(snapshot, borrower_id)

    dossier_id = await dossier_repo.save(
        _record(),
        snapshot_id,
        "BR-2026-B002",
        source_mode="bank",
        created_by_analyst_id=analyst_id,
    )

    orm = await pg_session.get(DossierORM, dossier_id)
    assert orm is not None
    assert orm.source_mode == "bank"
    assert orm.created_by_analyst_id == analyst_id


async def test_query_by_source_mode_index_works(pg_session: AsyncSession) -> None:
    """Smoke: index ``ix_dossiers_source_mode_created_at`` корректно покрывает фильтр."""
    snapshot = clean_borrower()
    borrower_repo = SqlAlchemyBorrowerRepository(pg_session)
    snapshot_repo = SqlAlchemyBorrowerSnapshotRepository(pg_session)
    dossier_repo = SqlAlchemyDossierRepository(pg_session)

    borrower_id = await borrower_repo.upsert(snapshot.borrower)
    snapshot_id = await snapshot_repo.save(snapshot, borrower_id)
    await dossier_repo.save(_record(), snapshot_id, "BR-2026-B003", source_mode="accountant")
    await dossier_repo.save(_record(), snapshot_id, "BR-2026-B004", source_mode="bank")
    await dossier_repo.save(_record(), snapshot_id, "BR-2026-B005", source_mode="bank")

    bank_count = (
        await pg_session.execute(
            select(DossierORM).where(DossierORM.source_mode == "bank")
        )
    ).scalars().all()
    assert len(bank_count) == 2
