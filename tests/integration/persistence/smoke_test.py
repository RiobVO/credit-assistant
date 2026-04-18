"""Smoke: фикстура поднимает контейнер, миграция применяется, SELECT возвращает 0 строк."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.borrower import BorrowerORM

pytestmark = pytest.mark.integration


async def test_pg_session_clean(pg_session: AsyncSession) -> None:
    rows = (await pg_session.execute(select(BorrowerORM))).all()
    assert rows == []
