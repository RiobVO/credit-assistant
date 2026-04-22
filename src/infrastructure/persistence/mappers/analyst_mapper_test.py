"""Unit: AnalystORM → AnalystIdentity без БД."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from infrastructure.persistence.mappers.analyst_mapper import analyst_from_orm
from infrastructure.persistence.models.analyst import AnalystORM


def test_analyst_from_orm_strips_password_hash() -> None:
    analyst_id = uuid4()
    orm = AnalystORM(
        id=analyst_id,
        email="ivanov@bank.uz",
        password_hash="$2b$12$dummyhash",
        full_name="Иванов И.И.",
        role="senior_analyst",
        is_active=True,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )

    identity = analyst_from_orm(orm)

    assert identity.id == analyst_id
    assert identity.email == "ivanov@bank.uz"
    assert identity.full_name == "Иванов И.И."
    assert identity.role == "senior_analyst"
    assert identity.is_active is True
    # Sanity: password_hash отсутствует в DTO API (frozen slots).
    assert not hasattr(identity, "password_hash")
