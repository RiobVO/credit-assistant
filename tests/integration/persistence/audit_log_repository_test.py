"""Integration: SqlAlchemyAuditLogRepository — append-only журнал событий."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.repositories.analyst_repository import (
    SqlAlchemyAnalystRepository,
)
from infrastructure.persistence.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)

pytestmark = pytest.mark.integration


async def _make_analyst(pg_session: AsyncSession, email: str = "a@bank.uz") -> UUID:
    repo = SqlAlchemyAnalystRepository(pg_session)
    return await repo.add(email=email, password_hash="$2b$12$x", full_name="A")


async def test_record_with_analyst_and_payload(pg_session: AsyncSession) -> None:
    analyst_id = await _make_analyst(pg_session)
    audit = SqlAlchemyAuditLogRepository(pg_session)

    event_id = await audit.record(
        event="login",
        analyst_id=analyst_id,
        payload={"ip": "10.0.0.1"},
    )

    rows = await audit.list_by_analyst(analyst_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.id == event_id
    assert row.event == "login"
    assert row.payload == {"ip": "10.0.0.1"}
    assert row.target_id is None
    assert row.target_type is None


async def test_record_login_failed_without_analyst_id(pg_session: AsyncSession) -> None:
    """`login_failed` пишется до того, как известен analyst — analyst_id NULL."""
    audit = SqlAlchemyAuditLogRepository(pg_session)

    await audit.record(
        event="login_failed",
        payload={"email": "unknown@bank.uz", "ip": "10.0.0.2"},
    )
    # Не падает — analyst_id nullable.


async def test_record_dossier_view_with_target(pg_session: AsyncSession) -> None:
    analyst_id = await _make_analyst(pg_session, email="b@bank.uz")
    audit = SqlAlchemyAuditLogRepository(pg_session)
    target_dossier_id = uuid4()

    await audit.record(
        event="view_dossier",
        analyst_id=analyst_id,
        target_type="dossier",
        target_id=target_dossier_id,
        payload={"masked_inn": "XXXXXX1234"},
    )

    rows = await audit.list_by_analyst(analyst_id)
    assert len(rows) == 1
    assert rows[0].target_type == "dossier"
    assert rows[0].target_id == target_dossier_id


async def test_list_by_analyst_orders_desc_by_created_at(pg_session: AsyncSession) -> None:
    analyst_id = await _make_analyst(pg_session, email="c@bank.uz")
    audit = SqlAlchemyAuditLogRepository(pg_session)

    await audit.record(event="login", analyst_id=analyst_id)
    await audit.record(event="search_borrower", analyst_id=analyst_id)
    await audit.record(event="logout", analyst_id=analyst_id)

    rows = await audit.list_by_analyst(analyst_id)
    assert [r.event for r in rows] == ["logout", "search_borrower", "login"]


async def test_list_by_analyst_respects_limit(pg_session: AsyncSession) -> None:
    analyst_id = await _make_analyst(pg_session, email="d@bank.uz")
    audit = SqlAlchemyAuditLogRepository(pg_session)
    for _ in range(5):
        await audit.record(event="login", analyst_id=analyst_id)

    rows = await audit.list_by_analyst(analyst_id, limit=2)
    assert len(rows) == 2


# T1.4 (ADR-0018) — brand_id forensics.


async def test_brand_id_defaults_to_default(pg_session: AsyncSession) -> None:
    """Без явного brand_id repo пишет server_default 'default'."""
    audit = SqlAlchemyAuditLogRepository(pg_session)
    analyst_id = await _make_analyst(pg_session, email="brand-default@bank.uz")

    await audit.record(event="login", analyst_id=analyst_id)

    rows = await audit.list_by_analyst(analyst_id)
    assert rows[0].brand_id == "default"


async def test_brand_id_persists_when_passed_to_constructor(
    pg_session: AsyncSession,
) -> None:
    """T1.4: brand_id, переданный в конструктор repo, попадает в каждую запись."""
    audit = SqlAlchemyAuditLogRepository(pg_session, brand_id="uzbekbank")
    analyst_id = await _make_analyst(pg_session, email="brand-uzbek@bank.uz")

    await audit.record(event="login", analyst_id=analyst_id)
    await audit.record(event="logout", analyst_id=analyst_id)

    rows = await audit.list_by_analyst(analyst_id)
    assert len(rows) == 2
    assert all(row.brand_id == "uzbekbank" for row in rows)


async def test_brand_id_isolated_between_repo_instances(
    pg_session: AsyncSession,
) -> None:
    """Forensics: два repo с разными brand_id пишут разные метки в одной БД.

    Это smoke-проверка для cross-contamination detection: если оператор
    miswired DATABASE_URL, audit-log покажет mismatch brand-метки.
    """
    audit_default = SqlAlchemyAuditLogRepository(pg_session, brand_id="default")
    audit_uzbek = SqlAlchemyAuditLogRepository(pg_session, brand_id="uzbekbank")
    analyst_id = await _make_analyst(pg_session, email="brand-cross@bank.uz")

    await audit_default.record(event="login", analyst_id=analyst_id)
    await audit_uzbek.record(event="login", analyst_id=analyst_id)

    rows = await audit_default.list_by_analyst(analyst_id)
    brand_ids = {row.brand_id for row in rows}
    assert brand_ids == {"default", "uzbekbank"}
