"""AnalystORM ↔ AnalystIdentity DTO.

``password_hash`` остаётся только в инфраструктуре — DTO не несёт credentials.
Используется AuthnAdapter после verify(password, password_hash).
"""

from __future__ import annotations

from application.dto.analyst_identity import AnalystIdentity
from infrastructure.persistence.models.analyst import AnalystORM


def analyst_from_orm(orm: AnalystORM) -> AnalystIdentity:
    return AnalystIdentity(
        id=orm.id,
        email=orm.email,
        full_name=orm.full_name,
        role=orm.role,
        is_active=orm.is_active,
    )
