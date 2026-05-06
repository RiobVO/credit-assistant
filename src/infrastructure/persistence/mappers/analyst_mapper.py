"""AnalystORM ↔ AnalystIdentity DTO.

``password_hash`` остаётся только в инфраструктуре — DTO не несёт credentials.
Используется AuthnAdapter после verify(password, password_hash).
"""

from __future__ import annotations

from application.dto.analyst_identity import AnalystIdentity
from infrastructure.persistence.models.analyst import AnalystORM


def analyst_from_orm(orm: AnalystORM) -> AnalystIdentity:
    # `mfa_enabled` в API computed-from-enrolled_at: secret в БД не означает
    # завершённый enrollment — /enroll/start пишет secret до verify. Только
    # после успешного /enroll/verify ставится mfa_enrolled_at = now() — это
    # и есть «реально включено».
    # Раньше (до этого fix'а) был computed-from-secret, что приводило к
    # half-enrolled bug: scan QR → invalid code → secret в БД → API
    # рапортует mfa_enabled=true → следующий login требует TOTP, но user
    # не сохранил secret в authenticator → lockout.
    real_mfa_enabled = orm.mfa_enrolled_at is not None
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
