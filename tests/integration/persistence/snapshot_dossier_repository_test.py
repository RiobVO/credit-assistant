"""Integration: BorrowerSnapshotRepository + DossierRepository против real Postgres.

Особо проверяется JSONB-сериализация Decimal/date → str (через json_serializer
engine'a) и FK ON DELETE RESTRICT для snapshot без borrower'а.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
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


async def test_snapshot_roundtrip_preserves_decimal_and_dates(
    pg_session: AsyncSession,
) -> None:
    """payload в JSONB пишется через json_serializer (Decimal→str), читается
    обратно через snapshot_from_payload — domain получает идентичный объект.
    """
    borrower_repo = SqlAlchemyBorrowerRepository(pg_session)
    snapshot_repo = SqlAlchemyBorrowerSnapshotRepository(pg_session)

    snapshot = clean_borrower()
    borrower_id = await borrower_repo.upsert(snapshot.borrower)
    snapshot_id = await snapshot_repo.save(snapshot, borrower_id)

    fetched = await snapshot_repo.get_by_id(snapshot_id)
    assert fetched is not None
    # buyer_revenue_share — Decimal значения, проверяем что не потеряны.
    assert fetched.buyer_revenue_share == snapshot.buyer_revenue_share
    assert all(isinstance(v, Decimal) for v in fetched.buyer_revenue_share.values())
    assert fetched.as_of == snapshot.as_of
    # Quarterly periods — DateRange c date.
    assert fetched.quarterly_reports[0].period.start == snapshot.quarterly_reports[0].period.start


async def test_snapshot_without_borrower_violates_fk(pg_session: AsyncSession) -> None:
    snapshot_repo = SqlAlchemyBorrowerSnapshotRepository(pg_session)
    snapshot = clean_borrower()

    with pytest.raises(IntegrityError):
        await snapshot_repo.save(snapshot, uuid4())


async def test_snapshot_get_by_unknown_id_returns_none(pg_session: AsyncSession) -> None:
    snapshot_repo = SqlAlchemyBorrowerSnapshotRepository(pg_session)
    assert await snapshot_repo.get_by_id(uuid4()) is None


async def test_dossier_save_and_get_roundtrips_red_flags_jsonb(
    pg_session: AsyncSession,
) -> None:
    """red_flags хранятся как JSONB list[dict]; severity_breakdown — JSONB dict.
    После round-trip enum severity восстанавливается, evidence Decimal — str.
    """
    borrower_repo = SqlAlchemyBorrowerRepository(pg_session)
    snapshot_repo = SqlAlchemyBorrowerSnapshotRepository(pg_session)
    dossier_repo = SqlAlchemyDossierRepository(pg_session)

    snapshot = clean_borrower()
    borrower_id = await borrower_repo.upsert(snapshot.borrower)
    snapshot_id = await snapshot_repo.save(snapshot, borrower_id)

    record = DossierRecord(
        score=42,
        recommendation="review",
        severity_breakdown={"high": 1, "medium": 2},
        red_flags=(
            RedFlag(
                rule_id="REVENUE_DROP_MOM_30",
                rule_version="v1",
                severity=FlagSeverity.HIGH,
                source="ЦБ РУз №27-п",
                message="Падение выручки 35% MoM",
                evidence={"drop_pct": Decimal("0.35"), "month": date(2026, 4, 1)},
                detected_at=date(2026, 5, 8),
            ),
        ),
        rules_version="v1",
        rules_evaluated=17,
    )
    dossier_id = await dossier_repo.save(record, snapshot_id, "BR-2026-A001")

    fetched = await dossier_repo.get_by_id(dossier_id)
    assert fetched is not None
    assert fetched.score == 42
    assert fetched.recommendation == "review"
    assert fetched.severity_breakdown == {"high": 1, "medium": 2}
    assert len(fetched.red_flags) == 1
    flag = fetched.red_flags[0]
    assert flag.rule_id == "REVENUE_DROP_MOM_30"
    assert flag.severity is FlagSeverity.HIGH
    assert flag.detected_at == date(2026, 5, 8)
    # evidence типизирован как dict[str, Any]; контракта на восстановление
    # Decimal/date нет (mapper передаёт значения как-есть из JSONB).
    # Проверяем только что ключи не потерялись и формат предсказуемый.
    assert flag.evidence["drop_pct"] == "0.35"
    assert flag.evidence["month"] == "2026-04-01"


async def test_dossier_get_by_unknown_id_returns_none(pg_session: AsyncSession) -> None:
    dossier_repo = SqlAlchemyDossierRepository(pg_session)
    assert await dossier_repo.get_by_id(uuid4()) is None
