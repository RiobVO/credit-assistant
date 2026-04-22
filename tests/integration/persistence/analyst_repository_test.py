"""Integration: SqlAlchemyAnalystRepository против real Postgres."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.repositories.analyst_repository import (
    SqlAlchemyAnalystRepository,
)

pytestmark = pytest.mark.integration


async def test_add_and_get_by_id_round_trip(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyAnalystRepository(pg_session)

    analyst_id = await repo.add(
        email="ivanov@bank.uz",
        password_hash="$2b$12$dummyhash",
        full_name="Иванов И.И.",
        role="senior_analyst",
    )

    identity = await repo.get_by_id(analyst_id)
    assert identity is not None
    assert identity.email == "ivanov@bank.uz"
    assert identity.full_name == "Иванов И.И."
    assert identity.role == "senior_analyst"
    assert identity.is_active is True


async def test_get_by_email_returns_identity_without_hash(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyAnalystRepository(pg_session)
    await repo.add(
        email="petrov@bank.uz",
        password_hash="$2b$12$secret",
        full_name="Петров П.П.",
    )

    identity = await repo.get_by_email("petrov@bank.uz")
    assert identity is not None
    assert identity.email == "petrov@bank.uz"
    assert not hasattr(identity, "password_hash")


async def test_get_by_email_with_hash_returns_orm(pg_session: AsyncSession) -> None:
    """AuthnAdapter использует этот метод для verify(password). Возвращается ORM."""
    repo = SqlAlchemyAnalystRepository(pg_session)
    await repo.add(
        email="sidorov@bank.uz",
        password_hash="$2b$12$known_hash",
        full_name="Сидоров С.С.",
    )

    orm = await repo.get_by_email_with_hash("sidorov@bank.uz")
    assert orm is not None
    assert orm.password_hash == "$2b$12$known_hash"


async def test_get_by_unknown_email_returns_none(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyAnalystRepository(pg_session)
    assert await repo.get_by_email("nobody@bank.uz") is None
    assert await repo.get_by_email_with_hash("nobody@bank.uz") is None


async def test_get_by_unknown_id_returns_none(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyAnalystRepository(pg_session)
    assert await repo.get_by_id(uuid4()) is None


async def test_duplicate_email_rejected(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyAnalystRepository(pg_session)
    await repo.add(
        email="dup@bank.uz",
        password_hash="$2b$12$a",
        full_name="A",
    )
    with pytest.raises(IntegrityError):
        await repo.add(
            email="dup@bank.uz",
            password_hash="$2b$12$b",
            full_name="B",
        )
