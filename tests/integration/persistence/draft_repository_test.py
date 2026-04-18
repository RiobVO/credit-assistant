"""Integration: DraftRepository против real Postgres.

Покрытие:
* create + get round-trip.
* update сдвигает expires_at и меняет payload.
* update unknown id → False.
* get для истёкшего draft → None (хотя строка в БД есть).
* purge_expired удаляет истёкшие, оставляет живые.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.draft import DraftORM
from infrastructure.persistence.repositories.draft_repository import (
    SqlAlchemyDraftRepository,
)

pytestmark = pytest.mark.integration


async def test_create_and_get_roundtrip(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyDraftRepository(pg_session)
    draft_id = await repo.create({"step1": {"inn": "123456789"}, "draft": True})

    fetched = await repo.get(draft_id)
    assert fetched == {"step1": {"inn": "123456789"}, "draft": True}


async def test_update_changes_payload_and_extends_ttl(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyDraftRepository(pg_session)
    draft_id = await repo.create({"step1": {"name": "Original"}})

    # Зафиксируем expires_at до апдейта, потом сравним.
    orig = await pg_session.get(DraftORM, draft_id)
    assert orig is not None
    expires_before = orig.expires_at

    ok = await repo.update(draft_id, {"step1": {"name": "Updated"}})
    assert ok is True

    after = await pg_session.get(DraftORM, draft_id)
    assert after is not None
    assert after.expires_at >= expires_before
    fetched = await repo.get(draft_id)
    assert fetched == {"step1": {"name": "Updated"}}


async def test_update_returns_false_for_unknown_id(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyDraftRepository(pg_session)
    assert await repo.update(uuid4(), {"any": "data"}) is False


async def test_get_returns_none_for_expired_draft(pg_session: AsyncSession) -> None:
    """TTL истёк — `get` возвращает None даже если строка ещё в БД (purge отдельно)."""
    repo = SqlAlchemyDraftRepository(pg_session)
    draft_id = await repo.create({"k": "v"})

    # Backdating expires_at напрямую через ORM — обходим _new_expiry repo.
    orm = await pg_session.get(DraftORM, draft_id)
    assert orm is not None
    orm.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await pg_session.flush()

    assert await repo.get(draft_id) is None


async def test_purge_expired_removes_only_expired(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyDraftRepository(pg_session)
    live_id = await repo.create({"live": True})
    expired_id = await repo.create({"expired": True})

    # Backdating только expired draft.
    expired_orm = await pg_session.get(DraftORM, expired_id)
    assert expired_orm is not None
    expired_orm.expires_at = datetime.now(UTC) - timedelta(days=1)
    await pg_session.flush()

    deleted = await repo.purge_expired()
    assert deleted == 1

    remaining = (await pg_session.execute(select(DraftORM.id))).scalars().all()
    assert live_id in remaining
    assert expired_id not in remaining
