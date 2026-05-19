"""Integration: BorrowerRepository против real Postgres."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.borrower import Borrower, LegalForm
from domain.value_objects.inn import INN
from infrastructure.persistence.repositories.borrower_repository import (
    SqlAlchemyBorrowerRepository,
)

pytestmark = pytest.mark.integration


def _make_borrower(
    inn: str = "100000001",
    name: str = 'OOO "Original"',
) -> Borrower:
    return Borrower(
        inn=INN(inn),
        name=name,
        legal_form=LegalForm.LLC,
        registration_date=date(2020, 1, 1),
        director_name="Ivanov I.I.",
        director_appointed_at=date(2021, 6, 1),
        oked_main="62.01",
        registered_address="Tashkent, ul. Amir Temur 1",
    )


async def test_upsert_inserts_new_borrower(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyBorrowerRepository(pg_session)
    borrower = _make_borrower()

    new_id = await repo.upsert(borrower)

    fetched = await repo.get_by_inn(INN("100000001"))
    assert fetched is not None
    assert fetched.name == 'OOO "Original"'
    by_id = await repo.get_by_id(new_id)
    assert by_id is not None and by_id.inn.value == "100000001"


async def test_upsert_updates_existing_borrower_with_same_inn(
    pg_session: AsyncSession,
) -> None:
    repo = SqlAlchemyBorrowerRepository(pg_session)

    first_id = await repo.upsert(_make_borrower(name='OOO "Original"'))
    second_id = await repo.upsert(_make_borrower(name='OOO "Renamed"'))

    # ON CONFLICT DO UPDATE возвращает существующий id, не создаёт новый.
    assert first_id == second_id
    fetched = await repo.get_by_inn(INN("100000001"))
    assert fetched is not None and fetched.name == 'OOO "Renamed"'


async def test_get_by_inn_returns_none_for_unknown(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyBorrowerRepository(pg_session)
    assert await repo.get_by_inn(INN("999999999")) is None


async def test_get_by_id_returns_none_for_unknown(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyBorrowerRepository(pg_session)
    assert await repo.get_by_id(uuid4()) is None
