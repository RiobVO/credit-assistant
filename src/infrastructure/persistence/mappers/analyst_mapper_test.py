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
    # mfa_enabled computed-from-enrolled_at: нет enrolled_at → False
    # (даже если stored bool=True).
    assert identity.mfa_enabled is False
    # Sanity: password_hash отсутствует в DTO API (frozen slots).
    assert not hasattr(identity, "password_hash")


def test_analyst_from_orm_mfa_enabled_when_enrolled() -> None:
    """После успешного /enroll/verify mfa_enabled=True (enrolled_at != None)."""
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
        # CA-DS16: stored bool удалён, computed flag = bool(enrolled_at).
        mfa_secret="JBSWY3DPEHPK3PXP",
        mfa_enrolled_at=now,
        mfa_backup_codes_hash=None,
    )
    identity = analyst_from_orm(orm)
    assert identity.mfa_enabled is True


def test_analyst_from_orm_mfa_disabled_when_half_enrolled() -> None:
    """Half-enrolled (secret есть, verify не сделан) → mfa_enabled=False.

    Это критичный invariant: backend /enroll/start пишет secret в БД до verify,
    и без этого теста computed_mfa_enabled был бы True уже на этапе scan-QR,
    что приводило к lockout-bug: user сканировал QR, ввёл неверный код,
    закрыл модалку → следующий login требовал TOTP, но secret в authenticator
    не сохранён → невозможно войти.
    """
    from infrastructure.persistence.mappers.analyst_mapper import analyst_from_orm

    now = datetime.now(tz=UTC)
    orm = AnalystORM(
        id=uuid4(),
        email="half@bank.uz",
        password_hash="$2b$12$h",
        full_name="Half Enrolled",
        role="analyst",
        is_active=True,
        created_at=now,
        updated_at=now,
        password_changed_at=now,
        mfa_secret="JBSWY3DPEHPK3PXP",  # secret записан /enroll/start
        mfa_enrolled_at=None,  # но verify не прошёл — enrolled_at NULL
        mfa_backup_codes_hash=None,
    )
    identity = analyst_from_orm(orm)
    assert identity.mfa_enabled is False
