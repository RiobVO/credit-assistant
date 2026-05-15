"""AuthnPort: контракт аутентификации аналитика.

v1 — SeededAuthnAdapter (БД + bcrypt). T1.5 — LdapAuthnAdapter +
BreakGlassAuthnAdapter (composite). Use case ``AuthenticateAnalyst``
не знает, откуда identity, но получает источник для audit-log trail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from application.dto.analyst_identity import AnalystIdentity

AuthnSource = Literal["seeded", "ldap", "break_glass"]


@dataclass(frozen=True, slots=True)
class AuthnResult:
    """T1.5 (ADR-0019): identity + source для audit-log compliance.

    ``source`` различает три флоу:
    * ``seeded`` — local bcrypt при ``AUTHN_MODE=seeded``.
    * ``ldap`` — LDAP bind+search при ``AUTHN_MODE=ldap`` для не-whitelist email'ов.
    * ``break_glass`` — local bcrypt при ``AUTHN_MODE=ldap`` для email в
      ``ADMIN_BREAK_GLASS_EMAILS`` whitelist. Compliance audit подсвечивает
      такие events отдельно.
    """

    identity: AnalystIdentity
    source: AuthnSource


class AuthnPort(Protocol):
    async def authenticate(
        self, email: str, password: str
    ) -> AuthnResult | None:
        """Возвращает (identity, source) при успешной проверке, иначе None.

        Не выбрасывает: разница между "пользователь не найден" и "пароль неверен"
        наружу не утекает — это предотвращает enumeration атаки.
        """
        ...
