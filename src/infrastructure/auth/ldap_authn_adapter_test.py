"""Unit-тесты LdapAuthnAdapter с mock LDAP-connection.

T1.5.1 / ADR-0019. Mock-based — реальный LDAP-сервер не поднимается в тестах.
Testcontainers openldap defer'ится в T1.5b backlog. Production smoke на
live-LDAP делается при инсталляции на конкретный bank-инфра.

Mock cover'ит ключевые adapter-ветки:
* successful bind+search+group-resolution → AnalystIdentity.
* user-bind fail (wrong password) → None.
* user not found in search → None.
* user found но не в required group → None.
* service-bind fail → LdapBindError (caller'у решать как trace'ить).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from application.dto.analyst_identity import AnalystIdentity
from infrastructure.auth.ldap_authn_adapter import (
    LdapAuthnAdapter,
    LdapBindError,
    LdapClient,
    LdapSettings,
)


class _FakeAnalystUpsertRepo:
    """Минимальный fake для analyst-provisioning seam.

    T1.5.2 заменит реальной repo'й, сейчас контракт = единственный метод
    ``upsert_from_ldap`` возвращает AnalystIdentity. Это позволяет T1.5.1
    собраться без миграции БД.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self._next_id = uuid4()

    async def upsert_from_ldap(
        self, email: str, full_name: str, role: str
    ) -> AnalystIdentity:
        self.calls.append((email, full_name, role))
        now = datetime.now(tz=UTC)
        return AnalystIdentity(
            id=self._next_id,
            email=email,
            full_name=full_name,
            role=role,
            is_active=True,
            created_at=now,
            password_changed_at=now,
            mfa_enabled=False,
        )


def _settings() -> LdapSettings:
    return LdapSettings(
        uri="ldap://ldap.bank.uz:389",
        base_dn="DC=bank,DC=uz",
        bind_dn="CN=svc,CN=Users,DC=bank,DC=uz",
        bind_password="svc-pass",
        user_search_filter="(&(objectClass=user)(mail={email}))",
        role_analyst_group="CN=Analysts,CN=Groups,DC=bank,DC=uz",
        role_senior_analyst_group="CN=SeniorAnalysts,CN=Groups,DC=bank,DC=uz",
    )


def _user_entry(
    *,
    dn: str = "CN=Ivanov,CN=Users,DC=bank,DC=uz",
    full_name: str = "Иванов И.И.",
    member_of: list[str] | None = None,
) -> dict[str, object]:
    return {
        "dn": dn,
        "attributes": {
            "displayName": full_name,
            "memberOf": member_of or [],
        },
    }


def _make_client_mock(
    *,
    service_bind_ok: bool = True,
    search_result: dict[str, object] | None = None,
    user_bind_ok: bool = True,
) -> MagicMock:
    """Собирает MagicMock, имитирующий sync LdapClient methods."""
    client = MagicMock(spec=LdapClient)

    if not service_bind_ok:
        client.search_user.side_effect = LdapBindError("service bind failed")
    else:
        client.search_user.return_value = search_result

    if not user_bind_ok:
        client.verify_password.return_value = False
    else:
        client.verify_password.return_value = True

    return client


async def test_successful_bind_returns_identity_with_senior_role() -> None:
    """Happy path: search нашёл user'а, password verify OK, user в senior группе."""
    settings = _settings()
    client = _make_client_mock(
        search_result=_user_entry(
            member_of=[
                settings.role_senior_analyst_group,
                "CN=AllUsers,CN=Groups,DC=bank,DC=uz",
            ],
        ),
    )
    repo = _FakeAnalystUpsertRepo()
    adapter = LdapAuthnAdapter(client, settings, repo)

    identity = await adapter.authenticate("ivanov@bank.uz", "real-pass")

    assert identity is not None
    assert identity.email == "ivanov@bank.uz"
    assert identity.full_name == "Иванов И.И."
    assert identity.role == "senior_analyst"
    assert repo.calls == [("ivanov@bank.uz", "Иванов И.И.", "senior_analyst")]


async def test_successful_bind_returns_identity_with_analyst_role() -> None:
    """User в analyst-group, не в senior-group → role=analyst."""
    settings = _settings()
    client = _make_client_mock(
        search_result=_user_entry(
            member_of=[settings.role_analyst_group],
        ),
    )
    repo = _FakeAnalystUpsertRepo()
    adapter = LdapAuthnAdapter(client, settings, repo)

    identity = await adapter.authenticate("petrov@bank.uz", "real-pass")

    assert identity is not None
    assert identity.role == "analyst"


async def test_user_not_found_returns_none() -> None:
    """search_user вернул None → authenticate возвращает None."""
    client = _make_client_mock(search_result=None)
    repo = _FakeAnalystUpsertRepo()
    adapter = LdapAuthnAdapter(client, _settings(), repo)

    identity = await adapter.authenticate("ghost@bank.uz", "any")

    assert identity is None
    assert repo.calls == []


async def test_wrong_password_returns_none() -> None:
    """User найден, но password verify (user-bind) fail → None."""
    client = _make_client_mock(
        search_result=_user_entry(
            member_of=["CN=Analysts,CN=Groups,DC=bank,DC=uz"],
        ),
        user_bind_ok=False,
    )
    repo = _FakeAnalystUpsertRepo()
    adapter = LdapAuthnAdapter(client, _settings(), repo)

    identity = await adapter.authenticate("ivanov@bank.uz", "wrong-pass")

    assert identity is None
    assert repo.calls == []


async def test_user_not_in_required_group_returns_none() -> None:
    """User найден и password правильный, но не в одной из role-групп → None."""
    client = _make_client_mock(
        search_result=_user_entry(
            member_of=["CN=AllUsers,CN=Groups,DC=bank,DC=uz"],
        ),
    )
    repo = _FakeAnalystUpsertRepo()
    adapter = LdapAuthnAdapter(client, _settings(), repo)

    identity = await adapter.authenticate("noaccess@bank.uz", "pass")

    assert identity is None
    assert repo.calls == []


async def test_service_bind_failure_propagates() -> None:
    """Service-bind fail = infra error. Adapter не должен молча скрывать его —
    callsite (authenticate_analyst) поймает и решит, что делать."""
    client = _make_client_mock(service_bind_ok=False)
    repo = _FakeAnalystUpsertRepo()
    adapter = LdapAuthnAdapter(client, _settings(), repo)

    with pytest.raises(LdapBindError):
        await adapter.authenticate("ivanov@bank.uz", "pass")


async def test_empty_member_of_returns_none() -> None:
    """memberOf отсутствует в LDAP entry → нет role → None."""
    client = _make_client_mock(search_result=_user_entry(member_of=[]))
    repo = _FakeAnalystUpsertRepo()
    adapter = LdapAuthnAdapter(client, _settings(), repo)

    identity = await adapter.authenticate("solo@bank.uz", "pass")

    assert identity is None
