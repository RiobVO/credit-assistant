"""AnalystORM ↔ AnalystIdentity DTO.

``password_hash`` остаётся только в инфраструктуре — DTO не несёт credentials.
Используется AuthnAdapter после verify(password, password_hash).
"""

from __future__ import annotations

from application.dto.analyst_identity import AnalystIdentity
from infrastructure.persistence.models.analyst import AnalystORM


def analyst_from_orm(orm: AnalystORM) -> AnalystIdentity:
    # CA-DS16: `mfa_enabled` в API = bool(mfa_enrolled_at). Stored bool
    # (`AnalystORM.mfa_enabled`) удалён миграцией 20260516_2030 — single
    # source of truth теперь только enrolled_at timestamp. Это инвариант:
    # half-enrolled state (secret записан /enroll/start, verify не прошёл)
    # → enrolled_at=NULL → mfa_enabled=False. Иначе был бы lockout bug:
    # user сканировал QR, ввёл неверный код, закрыл модалку → следующий
    # login требовал TOTP, но secret в authenticator не сохранён.
    return AnalystIdentity(
        id=orm.id,
        email=orm.email,
        full_name=orm.full_name,
        role=orm.role,
        is_active=orm.is_active,
        created_at=orm.created_at,
        password_changed_at=orm.password_changed_at,
        mfa_enabled=orm.mfa_enrolled_at is not None,
    )
