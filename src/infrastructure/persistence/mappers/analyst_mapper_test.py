"""Unit: AnalystORM → AnalystIdentity без БД."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from infrastructure.persistence.mappers.analyst_mapper import analyst_from_orm
from infrastructure.persistence.models.analyst import AnalystORM


def test_analyst_from_orm_strips_password_hash() -> None:
    analyst_id = uuid4()
    now = datetime.now(tz=UTC)
    orm = AnalystORM(
        id=analyst_id,
        email="ivanov@bank.uz",
        password_hash="$2b$12$dummyhash",
        full_name="Иванов И.И.",
        role="senior_analyst",
        is_active=True,
        created_at=now,
        updated_at=now,
        password_changed_at=now,
        mfa_enabled=False,
        mfa_secret=None,
        mfa_enrolled_at=None,
        mfa_backup_codes_hash=None,
    )

    identity = analyst_from_orm(orm)

    assert identity.id == analyst_id
    assert identity.email == "ivanov@bank.uz"
    assert identity.full_name == "Иванов И.И."
    assert identity.role == "senior_analyst"
    assert identity.is_active is True
    assert identity.created_at == now
    assert identity.password_changed_at == now
    # mfa_enabled computed-from-secret: нет secret → False (даже если stored bool=True).
    assert identity.mfa_enabled is False
    # Sanity: password_hash отсутствует в DTO API (frozen slots).
    assert not hasattr(identity, "password_hash")


def test_analyst_from_orm_mfa_enabled_when_secret_set() -> None:
    """После real enrollment'а mfa_enabled=True вычислен из наличия secret."""
    from infrastructure.persistence.mappers.analyst_mapper import analyst_from_orm

    now = datetime.now(tz=UTC)
    orm = AnalystORM(
        id=uuid4(),
        email="enrolled@bank.uz",
        password_hash="$2b$12$h",
        full_name="Enrolled User",
        role="analyst",
        is_active=True,
        created_at=now,
        updated_at=now,
        password_changed_at=now,
        # stored bool остался False — но computed flag True потому что secret есть.
        mfa_enabled=False,
        mfa_secret="JBSWY3DPEHPK3PXP",
        mfa_enrolled_at=now,
        mfa_backup_codes_hash=None,
    )
    identity = analyst_from_orm(orm)
    assert identity.mfa_enabled is True
