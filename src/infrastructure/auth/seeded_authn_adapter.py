"""SeededAuthnAdapter: AuthnPort через таблицу analysts + bcrypt verify."""

from __future__ import annotations

from application.ports.authn_port import AuthnResult
from infrastructure.auth.password_hasher import PasswordHasher
from infrastructure.persistence.mappers.analyst_mapper import analyst_from_orm
from infrastructure.persistence.repositories.analyst_repository import (
    SqlAlchemyAnalystRepository,
)

# Pre-computed валидный bcrypt-hash для пустой строки с cost=12.
# Используется как фиктивный target в ветке "user not found" для выравнивания
# времени отклика — иначе timing-разница утекает enumeration аналитиков.
_DUMMY_PASSWORD_HASH = "$2b$12$LfPQXnQz/.LiAo2nGw9CkOQyLh1J2.RBhsBM4ohbW1uW9Ipc/o7uS"


class SeededAuthnAdapter:
    """v1 implementation AuthnPort. Активных аналитиков сидят CLI'ем (4.B)."""

    def __init__(
        self,
        analyst_repo: SqlAlchemyAnalystRepository,
        hasher: PasswordHasher,
    ) -> None:
        self._analyst_repo = analyst_repo
        self._hasher = hasher

    async def authenticate(
        self, email: str, password: str
    ) -> AuthnResult | None:
        orm = await self._analyst_repo.get_by_email_with_hash(email)
        if orm is None:
            # Сравнение с заведомо неверным валидным bcrypt-hash. Время verify
            # эквивалентно реальной проверке — mitigation против user enumeration.
            self._hasher.verify(password, _DUMMY_PASSWORD_HASH)
            return None
        if not orm.is_active:
            return None
        # T1.5 (ADR-0019): LDAP-provisioned users держат password_hash=NULL —
        # SeededAdapter не верифицирует их. Timing-выравнивание через dummy hash.
        if orm.password_hash is None:
            self._hasher.verify(password, _DUMMY_PASSWORD_HASH)
            return None
        if not self._hasher.verify(password, orm.password_hash):
            return None
        return AuthnResult(identity=analyst_from_orm(orm), source="seeded")
