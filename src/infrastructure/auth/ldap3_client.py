"""Ldap3Client: производственная имплементация ``LdapClient`` поверх ldap3.

T1.5 / ADR-0019. Sync ldap3 — оборачивается в ``asyncio.to_thread`` в
``LdapAuthnAdapter``. Этот модуль blocking-only, никакого asyncio.

Pattern: per-call connection. Каждый ``search_user`` / ``verify_password``
создаёт новый ``ldap3.Connection``, делает работу, закрывает. Никаких
pool'ов: bank-internal scale (десятки операторов) делает overhead
несущественным, а short-lived connection избегает stale-session
проблем когда LDAP-сервер на сети нестабильный.

Production deployment работает с реальным AD/LDAP. Тесты — mock-only
(ldap_authn_adapter_test.py подменяет ``LdapClient`` через
``MagicMock(spec=LdapClient)``).
"""

from __future__ import annotations

import logging
from typing import Any, cast

from ldap3 import ALL_ATTRIBUTES, SIMPLE, SUBTREE, Connection, Server
from ldap3.core.exceptions import LDAPBindError, LDAPException

from infrastructure.auth.ldap_authn_adapter import (
    LdapBindError,
    LdapSearchError,
    LdapSettings,
)

logger = logging.getLogger(__name__)


class Ldap3Client:
    """Sync wrapper над ``ldap3.Connection``.

    Не реализует ``LdapClient`` Protocol через явное наследование —
    Protocol structural, type-check'ер сам убедится, что сигнатуры
    совпадают.
    """

    def __init__(self, settings: LdapSettings) -> None:
        self._settings = settings
        # Server-объект stateless: переиспользуем между запросами для
        # economy (DNS resolution + TLS handshake кэш).
        self._server = Server(settings.uri, get_info=None)

    def search_user(self, email: str) -> dict[str, object] | None:
        """Service-bind + search по email. None если не найден."""
        try:
            conn = Connection(
                self._server,
                user=self._settings.bind_dn,
                password=self._settings.bind_password,
                authentication=SIMPLE,
                auto_bind=True,
                read_only=True,
            )
        except LDAPBindError as exc:
            raise LdapBindError(
                f"LDAP service-bind failed: {exc}"
            ) from exc
        except LDAPException as exc:
            raise LdapBindError(
                f"LDAP service-bind raised non-bind error: {exc}"
            ) from exc

        try:
            ldap_filter = self._settings.user_search_filter.format(
                email=_escape_filter_value(email)
            )
            ok = conn.search(
                search_base=self._settings.base_dn,
                search_filter=ldap_filter,
                search_scope=SUBTREE,
                attributes=ALL_ATTRIBUTES,
            )
            if not ok or not conn.entries:
                return None
            entry = conn.entries[0]
            # ldap3 возвращает Entry-объекты; перегоняем в dict для
            # тестируемости (mock легче возвращает plain dict).
            attributes: dict[str, object] = {}
            for attr_name in entry.entry_attributes:
                values = entry[attr_name].values
                # entry[name].values всегда list; для single-value
                # атрибутов длина 1.
                attributes[attr_name] = (
                    values[0] if len(values) == 1 else list(values)
                )
            return {
                "dn": entry.entry_dn,
                "attributes": attributes,
            }
        except LDAPException as exc:
            raise LdapSearchError(f"LDAP search failed: {exc}") from exc
        finally:
            with _suppress_exceptions("connection unbind"):
                conn.unbind()

    def verify_password(self, user_dn: str, password: str) -> bool:
        """Пытается user-bind с указанным паролем. True/False по результату."""
        if not password:
            # ldap3 на пустой пароль делает anonymous-bind который проходит —
            # явный guard против ложного успеха.
            return False
        try:
            conn = Connection(
                self._server,
                user=user_dn,
                password=password,
                authentication=SIMPLE,
                auto_bind=True,
                read_only=True,
            )
        except LDAPBindError:
            return False
        except LDAPException as exc:
            logger.warning("LDAP user-bind raised non-bind error: %s", exc)
            return False

        ok = bool(cast("Any", conn).bound)
        with _suppress_exceptions("user-bind unbind"):
            conn.unbind()
        return ok


def _escape_filter_value(value: str) -> str:
    """Escape LDAP-filter специальных символов (RFC 4515 §3).

    Защита от LDAP-injection через email-параметр. ``ldap3`` имеет
    ``escape_filter_chars`` но мы держим минимальный subset
    inline для прозрачности.
    """
    replacements = {
        "\\": "\\5c",
        "*": "\\2a",
        "(": "\\28",
        ")": "\\29",
        "\x00": "\\00",
    }
    out: list[str] = []
    for ch in value:
        out.append(replacements.get(ch, ch))
    return "".join(out)


class _suppress_exceptions:
    """Context-manager: глотает любое исключение + logs warning.

    Используется для cleanup-операций (unbind), где исключение
    не должно ломать caller'а.
    """

    def __init__(self, label: str) -> None:
        self._label = label

    def __enter__(self) -> None:
        return None

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object
    ) -> bool:
        if exc is not None:
            logger.debug("suppressed %s: %s", self._label, exc)
        return True
