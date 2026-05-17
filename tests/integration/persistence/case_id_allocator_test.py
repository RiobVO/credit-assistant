"""Integration: CaseIdAllocator на real Postgres через testcontainers.

Покрывает то, что unit на stub-session дать не может:

* Чистая БД — first allocate выдаёт BR-{year}-0001.
* Последовательные allocate same-year monotonic 0001/0002/0003.
* Year rollover после backfilled MAX — sequence RESTART, новый счёт с 1.
* После rollover same-year продолжает с N+1 без повторного reset.

Outer-transaction откатывается в pg_session teardown → seed dossiers
не загрязняют другие тесты.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from application.services.case_id_allocator import SqlAlchemyCaseIdAllocator
from infrastructure.persistence.models.dossier import DossierORM
from infrastructure.persistence.repositories.borrower_repository import (
    SqlAlchemyBorrowerRepository,
)
from infrastructure.persistence.repositories.borrower_snapshot_repository import (
    SqlAlchemyBorrowerSnapshotRepository,
)
from tests.fixtures.synthetic_borrowers import clean_borrower

pytestmark = pytest.mark.integration


async def _seed_snapshot(pg_session: AsyncSession) -> tuple[object, object]:
    """Сидит borrower + snapshot, возвращает (borrower_id, snapshot_id)."""
    borrower_repo = SqlAlchemyBorrowerRepository(pg_session)
    snapshot_repo = SqlAlchemyBorrowerSnapshotRepository(pg_session)
    snapshot = clean_borrower()
    borrower_id = await borrower_repo.upsert(snapshot.borrower)
    snapshot_id = await snapshot_repo.save(snapshot, borrower_id)
    return borrower_id, snapshot_id


def _new_dossier_row(*, case_id: str, snapshot_id: object, created_at: datetime) -> DossierORM:
    return DossierORM(
        id=uuid4(),
        snapshot_id=snapshot_id,
        score=0,
        recommendation="approve",
        severity_breakdown={},
        red_flags=[],
        rules_version="v1",
        rules_evaluated=0,
        source_mode="accountant",
        created_by_analyst_id=None,
        case_id=case_id,
    )


async def _truncate_dossiers_and_reset_seq(pg_session: AsyncSession) -> None:
    """Готовим чистую сцену внутри savepoint: pg_session — outer-tx с
    savepoint, мы внутри. TRUNCATE dossiers RESTART IDENTITY нельзя
    (FK на borrower_snapshots), просто DELETE + setval'им sequence.
    """
    await pg_session.execute(text("DELETE FROM dossiers"))
    await pg_session.execute(text("SELECT setval('dossier_case_seq', 1, false)"))


async def test_allocate_first_ever_returns_0001(pg_session: AsyncSession) -> None:
    """Пустая таблица dossiers + sequence в начальном состоянии → BR-{year}-0001."""
    await _truncate_dossiers_and_reset_seq(pg_session)

    allocator = SqlAlchemyCaseIdAllocator(pg_session)
    case_id = await allocator.allocate(datetime(2026, 5, 18, tzinfo=UTC))

    assert case_id == "BR-2026-0001"


async def test_allocate_monotonic_same_year(pg_session: AsyncSession) -> None:
    """Три allocate подряд same-year → 0001, 0002, 0003."""
    await _truncate_dossiers_and_reset_seq(pg_session)

    allocator = SqlAlchemyCaseIdAllocator(pg_session)
    ids = [await allocator.allocate(datetime(2026, 5, 18, tzinfo=UTC)) for _ in range(3)]

    assert ids == ["BR-2026-0001", "BR-2026-0002", "BR-2026-0003"]


async def test_allocate_year_rollover_resets(pg_session: AsyncSession) -> None:
    """После BR-2026-0042 в БД, allocate с now.year=2027 → BR-2027-0001."""
    await _truncate_dossiers_and_reset_seq(pg_session)
    _, snapshot_id = await _seed_snapshot(pg_session)
    pg_session.add(
        _new_dossier_row(
            case_id="BR-2026-0042",
            snapshot_id=snapshot_id,
            created_at=datetime(2026, 12, 31, 23, 0, tzinfo=UTC),
        )
    )
    await pg_session.flush()
    # Sequence стоит «как-будто 42 уже выдано».
    await pg_session.execute(text("SELECT setval('dossier_case_seq', 42, true)"))

    allocator = SqlAlchemyCaseIdAllocator(pg_session)
    case_id = await allocator.allocate(datetime(2027, 1, 1, tzinfo=UTC))

    assert case_id == "BR-2027-0001"


async def test_allocate_continues_after_rollover(pg_session: AsyncSession) -> None:
    """После BR-2027-0001 в БД второй allocate same-year → BR-2027-0002."""
    await _truncate_dossiers_and_reset_seq(pg_session)
    _, snapshot_id = await _seed_snapshot(pg_session)
    pg_session.add(
        _new_dossier_row(
            case_id="BR-2027-0001",
            snapshot_id=snapshot_id,
            created_at=datetime(2027, 1, 1, tzinfo=UTC),
        )
    )
    await pg_session.flush()
    await pg_session.execute(text("SELECT setval('dossier_case_seq', 1, true)"))

    allocator = SqlAlchemyCaseIdAllocator(pg_session)
    case_id = await allocator.allocate(datetime(2027, 1, 2, tzinfo=UTC))

    assert case_id == "BR-2027-0002"
