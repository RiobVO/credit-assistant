"""Integration test для scripts.cleanup_test_data.

Сидит мусорные borrowers / analysts в real Postgres (testcontainer), вызывает
helpers cleanup-скрипта напрямую (без CLI entry-point), проверяет что:
* мусорные borrowers удалены + snapshots+dossiers каскадно;
* analyst.full_name == "T0.4 Smoke" переименован в "Demo Analyst";
* dry-run ничего не пишет;
* повторный прогон — no-op (idempotent).

Skip всего модуля если Docker недоступен — testcontainers conftest сам делает
session-level skip.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.analyst import AnalystORM
from infrastructure.persistence.models.borrower import BorrowerORM
from infrastructure.persistence.models.borrower_snapshot import BorrowerSnapshotORM
from infrastructure.persistence.models.dossier import DossierORM

from scripts.cleanup_test_data import (
    _delete_analysts,
    _delete_borrowers,
    _rename_analysts,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def _seed_borrower(session: AsyncSession, inn: str, name: str) -> BorrowerORM:
    """Минимальный borrower row через ORM (BorrowerRepository ожидает domain)."""
    b = BorrowerORM(
        id=uuid4(),
        inn=inn,
        name=name,
        legal_form="llc",
        registration_date=date(2020, 1, 1),
        director_name="Test Director",
        director_appointed_at=date(2021, 1, 1),
        oked_main="62.01",
        registered_address="Tashkent",
    )
    session.add(b)
    await session.flush()
    return b


async def _seed_snapshot(
    session: AsyncSession,
    borrower_id: UUID,
    payload: dict[str, object] | None = None,
) -> BorrowerSnapshotORM:
    snap = BorrowerSnapshotORM(
        id=uuid4(),
        borrower_id=borrower_id,
        as_of=date(2026, 1, 1),
        payload=payload or {"empty": True},
    )
    session.add(snap)
    await session.flush()
    return snap


async def _seed_dossier(
    session: AsyncSession, snapshot_id: UUID, case_id: str
) -> DossierORM:
    d = DossierORM(
        id=uuid4(),
        snapshot_id=snapshot_id,
        score=0,
        recommendation="approve",
        severity_breakdown={},
        red_flags=[],
        rules_version="v1",
        rules_evaluated=24,
        case_id=case_id,
        source_mode="bank",
    )
    session.add(d)
    await session.flush()
    return d


async def _seed_analyst(
    session: AsyncSession, email: str, full_name: str
) -> AnalystORM:
    a = AnalystORM(
        id=uuid4(),
        email=email,
        password_hash="$2b$12$dummy.bcrypt.hash.placeholder.0123456789ABCDEF",
        full_name=full_name,
        role="analyst",
        is_active=True,
    )
    session.add(a)
    await session.flush()
    return a


async def test_dry_run_does_not_modify_db(pg_session: AsyncSession) -> None:
    """Dry-run собирает счётчики и не пишет ничего в БД."""
    test_b = await _seed_borrower(pg_session, "999000001", "ЙЦУЙЦУЙЦУ")
    snap = await _seed_snapshot(pg_session, test_b.id)
    await _seed_dossier(pg_session, snap.id, "BR-2099-9999")
    await _seed_analyst(pg_session, "t04@bank.uz", "T0.4 Smoke")

    b, s, d = await _delete_borrowers(pg_session, dry_run=True)
    r = await _rename_analysts(pg_session, dry_run=True)

    # Счётчики сообщают про намерение, но борровер всё ещё в БД.
    assert b == 1
    assert s == 1
    assert d == 1
    assert r == 1

    still_there = (
        await pg_session.execute(
            select(BorrowerORM).where(BorrowerORM.name == "ЙЦУЙЦУЙЦУ")
        )
    ).scalar_one_or_none()
    assert still_there is not None, "dry-run должен оставить borrower в БД"

    analyst = (
        await pg_session.execute(
            select(AnalystORM).where(AnalystORM.email == "t04@bank.uz")
        )
    ).scalar_one()
    assert analyst.full_name == "T0.4 Smoke", "dry-run не должен переименовывать"


async def test_yes_deletes_borrowers_and_cascades(pg_session: AsyncSession) -> None:
    """Реальный прогон: borrower + snapshot + dossier удалены каскадно."""
    test_b = await _seed_borrower(pg_session, "999000002", "TEST")
    snap = await _seed_snapshot(pg_session, test_b.id)
    dossier = await _seed_dossier(pg_session, snap.id, "BR-2099-9998")

    real_b = await _seed_borrower(pg_session, "999000003", "ООО «Реальный»")

    await _delete_borrowers(pg_session, dry_run=False)

    test_left = (
        await pg_session.execute(
            select(BorrowerORM).where(BorrowerORM.id == test_b.id)
        )
    ).scalar_one_or_none()
    assert test_left is None, "TEST-borrower должен быть удалён"

    snap_left = (
        await pg_session.execute(
            select(BorrowerSnapshotORM).where(BorrowerSnapshotORM.id == snap.id)
        )
    ).scalar_one_or_none()
    assert snap_left is None, "snapshot тестового borrower'а удалён каскадно"

    dossier_left = (
        await pg_session.execute(
            select(DossierORM).where(DossierORM.id == dossier.id)
        )
    ).scalar_one_or_none()
    assert dossier_left is None, "dossier тестового borrower'а удалён каскадно"

    real_left = (
        await pg_session.execute(
            select(BorrowerORM).where(BorrowerORM.id == real_b.id)
        )
    ).scalar_one_or_none()
    assert real_left is not None, "реальный borrower не должен трогаться"


async def test_yes_renames_t04_smoke_analyst(pg_session: AsyncSession) -> None:
    """Аналитик t04@bank.uz получает full_name 'Demo Analyst' вместо 'T0.4 Smoke'."""
    await _seed_analyst(pg_session, "t04@bank.uz", "T0.4 Smoke")

    renamed = await _rename_analysts(pg_session, dry_run=False)
    assert renamed == 1

    a = (
        await pg_session.execute(
            select(AnalystORM).where(AnalystORM.email == "t04@bank.uz")
        )
    ).scalar_one()
    assert a.full_name == "Demo Analyst"


async def test_yes_is_idempotent(pg_session: AsyncSession) -> None:
    """Повторный прогон ничего не находит → счётчики == 0."""
    await _seed_borrower(pg_session, "999000004", "OOO Test T1.1")
    await _delete_borrowers(pg_session, dry_run=False)

    b, s, d = await _delete_borrowers(pg_session, dry_run=False)
    assert (b, s, d) == (0, 0, 0)


async def test_blacklist_analyst_with_dossier_is_skipped(
    pg_session: AsyncSession,
) -> None:
    """Аналитик из ANALYST_BLACKLIST с привязанным dossier не удаляется."""
    analyst = await _seed_analyst(pg_session, "smoke@bank.uz", "T1.1 Smoke Tester")
    b = await _seed_borrower(pg_session, "999000005", "ООО «Другой»")
    snap = await _seed_snapshot(pg_session, b.id)
    d = DossierORM(
        id=uuid4(),
        snapshot_id=snap.id,
        score=0,
        recommendation="approve",
        severity_breakdown={},
        red_flags=[],
        rules_version="v1",
        rules_evaluated=24,
        case_id="BR-2099-9997",
        source_mode="bank",
        created_by_analyst_id=analyst.id,
    )
    pg_session.add(d)
    await pg_session.flush()

    deleted = await _delete_analysts(pg_session, dry_run=False)
    assert deleted == 0, "analyst с dossier-trail удалять нельзя"

    a = (
        await pg_session.execute(
            select(AnalystORM).where(AnalystORM.id == analyst.id)
        )
    ).scalar_one_or_none()
    assert a is not None
