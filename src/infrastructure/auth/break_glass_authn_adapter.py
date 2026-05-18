"""BreakGlassAuthnAdapter: композитный AuthnPort.

T1.5 / ADR-0019. В ``authn_mode=ldap`` deployment'е используется как
композиция:

* email в whitelist (``ADMIN_BREAK_GLASS_EMAILS``) → SeededAuthnAdapter
  (local bcrypt). Use-case: recovery когда LDAP-инфра недоступна или
  operator случайно потерял LDAP-доступ.
* email НЕ в whitelist → LdapAuthnAdapter.

Случаев "fallback" нет — это explicit switch. Audit-log пишет
``authn_source`` чтобы compliance-аудит видел break-glass usage
(T1.5.3 wiring).
"""

from __future__ import annotations

from application.dto.analyst_identity import AnalystIdentity
from application.ports.authn_port import AuthnPort


class BreakGlassAuthnAdapter:
    """Two-branch: email в whitelist → seeded, иначе → ldap."""

    def __init__(
        self,
        seeded: AuthnPort,
        ldap: AuthnPort,
        break_glass_emails: frozenset[str],
    ) -> None:
        self._seeded = seeded
        self._ldap = ldap
        # Case-insensitive matching: email'ы в LDAP/AD обычно сравниваются
        # без учёта регистра, чтобы avoid edge-case несовпадения.
        self._break_glass: frozenset[str] = frozenset(
            e.lower() for e in break_glass_emails
        )

    async def authenticate(
        self, email: str, password: str
    ) -> AnalystIdentity | None:
        if email.lower() in self._break_glass:
            return await self._seeded.authenticate(email, password)
        return await self._ldap.authenticate(email, password)


def parse_break_glass_emails(raw: str) -> frozenset[str]:
    """Парсит comma-separated env-string в frozenset нормализованных email'ов.

    Пустые токены и whitespace игнорируются. Дубликаты схлопываются.
    """
    if not raw:
        return frozenset()
    tokens = [token.strip() for token in raw.split(",")]
    return frozenset(token for token in tokens if token)
