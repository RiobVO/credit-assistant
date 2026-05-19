"""ORM для Analyst: банковский кредитный аналитик с seeded login/password.

В v1 — единственный auth-источник (mock SSO). В v2 заменяется LDAP/OAuth
адаптером, ORM остаётся для аудита и истории действий.
``password_hash`` — bcrypt cost ≥ 12 (см. ``infrastructure/auth/password_hasher``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.database import Base
from infrastructure.persistence.types.encrypted_string import EncryptedString


class AnalystORM(Base):
    """Банковский аналитик. Уникален по email."""

    __tablename__ = "analysts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # T1.5 (ADR-0019): NULL для LDAP-provisioned users — пароль владеется
    # LDAP-server'ом. SeededAuthnAdapter работает только с rows где
    # password_hash IS NOT NULL.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # T1.3 (ADR-0017): full_name шифруется через Fernet TypeDecorator.
    # Length 500 для Fernet token (255 plaintext → ~432 base64).
    full_name: Mapped[str] = mapped_column(EncryptedString(500), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="analyst")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Phase 5 Settings: трекинг свежести пароля. Update в
    # `POST /api/bank/auth/change-password` (см. auth.py).
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # CA-DS16: legacy `mfa_enabled` stored bool удалён (миграция
    # 20260516_2030). API `AnalystIdentity.mfa_enabled` остаётся как
    # computed = bool(mfa_enrolled_at) — единственный источник truth.

    # Phase 5.B — real TOTP 2FA (RFC 6238). См. миграцию 9a4d2e1f8b67.
    # `mfa_secret`: base32 shared secret. **T1.3 (ADR-0017, закрывает CA-DS12)**:
    # шифруется через Fernet TypeDecorator. Length 200 для Fernet token
    # (32 byte base32 → ~108 chars Fernet token).
    # `mfa_enrolled_at`: момент успешной первой verify; до enrollment'а NULL.
    # `mfa_backup_codes_hash`: JSON-массив bcrypt-хешей одноразовых recovery-кодов.
    mfa_secret: Mapped[str | None] = mapped_column(EncryptedString(200), nullable=True)
    mfa_enrolled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mfa_backup_codes_hash: Mapped[Any | None] = mapped_column(JSONB, nullable=True)

    # T1.5 (ADR-0019): источник аутентификации row'а. 'seeded' — local bcrypt
    # (password_hash NOT NULL); 'ldap' — LDAP-provisioned (password_hash NULL).
    # CHECK constraint в миграции ограничивает enum.
    authn_source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="seeded"
    )
