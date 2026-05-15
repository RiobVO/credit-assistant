"""LdapAuthnAdapter: AuthnPort через ldap3 bind+search.

T1.5 / ADR-0019. Два-phase pattern:

1. Service-bind по `bind_dn`/`bind_password` — для поиска user'а в каталоге.
2. Search по `user_search_filter` с подстановкой email → получаем DN +
   ``memberOf`` атрибут.
3. User-bind по найденному DN с user-password → проверка пароля.
4. Group → role mapping: senior_analyst_group → ``senior_analyst``,
   analyst_group → ``analyst``, иначе → fail.
5. Lazy upsert в local `analysts` table через ``AnalystUpsertPort`` —
   реализуется в T1.5.2.

Library `ldap3` — pure Python, blocking. Async обёртка через
``asyncio.to_thread``. На bank-инсталляции production будет работать
с реальным AD/LDAP, тесты — mock-only (testcontainers-openldap defer'ится
в T1.5b).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from application.dto.analyst_identity import AnalystIdentity
from application.ports.authn_port import AuthnResult


class LdapBindError(RuntimeError):
    """Service-bind или техническая LDAP-ошибка.

    Не путать с user-password fail — это инфраструктурная ошибка (LDAP
    недоступен, bind credentials неверны). Caller должен fail-closed:
    если LDAP не отвечает — аутентификация невозможна, а не fallback
    на seeded (это break-glass-only территория).
    """


class LdapSearchError(RuntimeError):
    """Поиск user'а упал на технике (не «не нашли», а «search failed»)."""


@dataclass(frozen=True, slots=True)
class LdapSettings:
    """Конфигурация LDAP-соединения, проверенная и резолвенная из env."""

    uri: str
    base_dn: str
    bind_dn: str
    bind_password: str
    user_search_filter: str
    role_analyst_group: str
    role_senior_analyst_group: str


class LdapClient(Protocol):
    """Sync LDAP client. Адаптер оборачивает в ``asyncio.to_thread``.

    Контракт минимальный: search_user + verify_password. Реальная
    имплементация в ``Ldap3Client`` ниже.
    """

    def search_user(self, email: str) -> dict[str, object] | None:
        """Service-bind + search по email. Returns dict со ключами
        ``dn`` и ``attributes``, или None если user не найден.

        Raises ``LdapBindError`` при service-bind fail, ``LdapSearchError``
        при технической ошибке поиска.
        """
        ...

    def verify_password(self, user_dn: str, password: str) -> bool:
        """User-bind: возвращает True если bind успешен (пароль верен)."""
        ...


class AnalystUpsertPort(Protocol):
    """Lazy provisioning user'а из LDAP в local `analysts` table.

    T1.5.1: контракт-only, fake-реализация в тестах. T1.5.2: реальная
    реализация через ``SqlAlchemyAnalystRepository.upsert_from_ldap``.
    """

    async def upsert_from_ldap(
        self, email: str, full_name: str, role: str
    ) -> AnalystIdentity:
        ...


class LdapAuthnAdapter:
    """AuthnPort: LDAP bind+search + lazy local provision."""

    def __init__(
        self,
        client: LdapClient,
        settings: LdapSettings,
        analyst_upsert: AnalystUpsertPort,
    ) -> None:
        self._client = client
        self._settings = settings
        self._upsert = analyst_upsert

    async def authenticate(
        self, email: str, password: str
    ) -> AuthnResult | None:
        # Service-bind + search. LdapBindError всплывает caller'у —
        # инфраструктурная проблема не маскируется под "wrong password".
        entry = await asyncio.to_thread(self._client.search_user, email)
        if entry is None:
            return None

        user_dn = str(entry["dn"])
        attributes = entry["attributes"]
        if not isinstance(attributes, dict):
            raise LdapSearchError(f"unexpected attributes shape for {user_dn}")

        # Резолвим role до verify_password — экономим один LDAP roundtrip,
        # если user не в нужных группах.
        role = self._resolve_role(attributes)
        if role is None:
            return None

        password_ok = await asyncio.to_thread(
            self._client.verify_password, user_dn, password
        )
        if not password_ok:
            return None

        full_name = self._resolve_full_name(attributes, fallback=email)
        identity = await self._upsert.upsert_from_ldap(
            email=email, full_name=full_name, role=role
        )
        return AuthnResult(identity=identity, source="ldap")

    def _resolve_role(self, attributes: dict[str, object]) -> str | None:
        """Senior precedence: если user в обеих группах — senior_analyst."""
        member_of_raw = attributes.get("memberOf", [])
        if isinstance(member_of_raw, str):
            member_of: list[str] = [member_of_raw]
        elif isinstance(member_of_raw, list):
            member_of = [str(g) for g in member_of_raw]
        else:
            return None

        if self._settings.role_senior_analyst_group in member_of:
            return "senior_analyst"
        if self._settings.role_analyst_group in member_of:
            return "analyst"
        return None

    @staticmethod
    def _resolve_full_name(attributes: dict[str, object], *, fallback: str) -> str:
        """displayName / cn / fallback в этом порядке. AD-конвенция."""
        for key in ("displayName", "cn"):
            value = attributes.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, str) and first.strip():
                    return first
        return fallback
