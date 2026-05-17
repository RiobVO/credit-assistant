"""Integration: SqlAlchemyDossierRepository.get_view_by_id поверх real Postgres.

Один SELECT с двумя JOIN: dossiers → borrower_snapshots → borrowers. Проверяем,
что вернувшийся ``DossierViewRecord`` совпадает по содержимому с тем, что было
сохранено через стандартную цепочку upsert/save/save.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.dossier_record import DossierRecord
from domain.entities.red_flag import RedFlag
from domain.value_objects.flag_severity import FlagSeverity
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


async def test_get_view_by_id_returns_full_record(pg_session: AsyncSession) -> None:
    """Round-trip: write → get_view_by_id → все три части совпадают по полям.

    Покрывает связку трёх mappers (borrower / snapshot / dossier) в одном запросе.
    """
    borrower_repo = SqlAlchemyBorrowerRepository(pg_session)
    snapshot_repo = SqlAlchemyBorrowerSnapshotRepository(pg_session)
    dossier_repo = SqlAlchemyDossierRepository(pg_session)

    snapshot = clean_borrower()
    borrower_id = await borrower_repo.upsert(snapshot.borrower)
    snapshot_id = await snapshot_repo.save(snapshot, borrower_id)

    record = DossierRecord(
        score=12,
        recommendation="approve",
        severity_breakdown={"low": 2, "medium": 1},
        red_flags=(
            RedFlag(
                rule_id="SINGLE_BUYER_CONCENTRATION",
                rule_version="v1",
                severity=FlagSeverity.MEDIUM,
                source="Базель III concentration risk",
                message="Топ-1 покупатель 0.42",
                evidence={"top1_share": Decimal("0.42")},
                detected_at=date(2026, 5, 8),
            ),
        ),
        rules_version="v1",
        rules_evaluated=17,
    )
    dossier_id = await dossier_repo.save(record, snapshot_id, "BR-2026-A002")

    view = await dossier_repo.get_view_by_id(dossier_id)
    assert view is not None

    # 1. dossier_id, created_at, case_id — из таблицы dossiers
    assert view.dossier_id == dossier_id
    assert isinstance(view.created_at, datetime)
    assert view.case_id == "BR-2026-A002"

    # 2. dossier (DossierRecord) — score, recommendation, red_flags восстановлены
    assert view.dossier.score == 12
    assert view.dossier.recommendation == "approve"
    assert view.dossier.severity_breakdown == {"low": 2, "medium": 1}
    assert len(view.dossier.red_flags) == 1
    flag = view.dossier.red_flags[0]
    assert flag.rule_id == "SINGLE_BUYER_CONCENTRATION"
    assert flag.severity is FlagSeverity.MEDIUM

    # 3. snapshot — borrower инжектится из join, payload восстанавливает остальное
    assert view.snapshot.borrower.inn == snapshot.borrower.inn
    assert view.snapshot.borrower.name == snapshot.borrower.name
    assert view.snapshot.as_of == snapshot.as_of
    assert view.snapshot.buyer_revenue_share == snapshot.buyer_revenue_share
    assert all(isinstance(v, Decimal) for v in view.snapshot.buyer_revenue_share.values())


async def test_get_view_by_unknown_id_returns_none(pg_session: AsyncSession) -> None:
    dossier_repo = SqlAlchemyDossierRepository(pg_session)
    assert await dossier_repo.get_view_by_id(uuid4()) is None
