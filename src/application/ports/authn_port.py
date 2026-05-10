"""AuthnPort: контракт аутентификации аналитика.

v1 — SeededAuthnAdapter (БД + bcrypt). v2 — LdapAuthnAdapter / OAuthAuthnAdapter,
тот же port. Use case ``AuthenticateAnalyst`` не знает, откуда identity.
"""

from __future__ import annotations

from typing import Protocol

from application.dto.analyst_identity import AnalystIdentity


class AuthnPort(Protocol):
    async def authenticate(
        self, email: str, password: str
    ) -> AnalystIdentity | None:
        """Возвращает identity при успешной проверке, иначе None.

        Не выбрасывает: разница между "пользователь не найден" и "пароль неверен"
        наружу не утекает — это предотвращает enumeration атаки.
        """
        ...
