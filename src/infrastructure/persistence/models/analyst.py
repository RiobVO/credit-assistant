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


class AnalystORM(Base):
    """Банковский аналитик. Уникален по email."""

    __tablename__ = "analysts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
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

    # Phase 5 Settings: трекинг свежести пароля.
    # `password_changed_at` обновляется будущим endpoint change-password (TODO[CA-068]).
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # `mfa_enabled` остался от Phase 5.A как stored bool, но **используется
    # только репозиторием для backward-compat** — в API mfa_enabled
    # вычисляется из ``bool(mfa_secret)``. Без real secret — нет TOTP enrollment.
    # Reseed admin'а с --mfa-enabled теперь no-op для UI; настоящее enrollment
    # делается через POST /api/bank/auth/mfa/enroll/start+verify.
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Phase 5.B — real TOTP 2FA (RFC 6238). См. миграцию 9a4d2e1f8b67.
    # `mfa_secret`: base32 shared secret, plain в БД (POC; production → vault, TODO[CA-DS12]).
    # `mfa_enrolled_at`: момент успешной первой verify; до enrollment'а NULL.
    # `mfa_backup_codes_hash`: JSON-массив bcrypt-хешей одноразовых recovery-кодов.
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mfa_enrolled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mfa_backup_codes_hash: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
