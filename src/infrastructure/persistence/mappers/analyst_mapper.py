"""AnalystORM ↔ AnalystIdentity DTO.

``password_hash`` остаётся только в инфраструктуре — DTO не несёт credentials.
Используется AuthnAdapter после verify(password, password_hash).
"""

from __future__ import annotations

from application.dto.analyst_identity import AnalystIdentity
from infrastructure.persistence.models.analyst import AnalystORM


def analyst_from_orm(orm: AnalystORM) -> AnalystIdentity:
    # `mfa_enabled` в API computed-from-secret: stored bool сжигается, если нет
    # real-enrollment'а. Это убирает security theater от Phase 5.A seed-flag'а.
    real_mfa_enabled = orm.mfa_secret is not None
    return AnalystIdentity(
        id=orm.id,
        email=orm.email,
        full_name=orm.full_name,
        role=orm.role,
        is_active=orm.is_active,
        created_at=orm.created_at,
        password_changed_at=orm.password_changed_at,
        mfa_enabled=real_mfa_enabled,
    )
