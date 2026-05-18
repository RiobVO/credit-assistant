"""Unit-тесты BreakGlassAuthnAdapter."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from application.dto.analyst_identity import AnalystIdentity
from infrastructure.auth.break_glass_authn_adapter import (
    BreakGlassAuthnAdapter,
    parse_break_glass_emails,
)


def _identity(email: str, *, role: str = "analyst") -> AnalystIdentity:
    now = datetime.now(tz=UTC)
    return AnalystIdentity(
        id=uuid4(),
        email=email,
        full_name="X",
        role=role,
        is_active=True,
        created_at=now,
        password_changed_at=now,
        mfa_enabled=False,
    )


class _Recorder:
    """Fake AuthnPort: запоминает вызовы + возвращает указанный identity."""

    def __init__(self, returns: AnalystIdentity | None) -> None:
        self.returns = returns
        self.calls: list[tuple[str, str]] = []

    async def authenticate(
        self, email: str, password: str
    ) -> AnalystIdentity | None:
        self.calls.append((email, password))
        return self.returns


async def test_email_in_whitelist_uses_seeded() -> None:
    expected = _identity("admin@bank.uz")
    seeded = _Recorder(returns=expected)
    ldap = _Recorder(returns=None)
    adapter = BreakGlassAuthnAdapter(
        seeded=seeded,
        ldap=ldap,
        break_glass_emails=frozenset({"admin@bank.uz"}),
    )

    identity = await adapter.authenticate("admin@bank.uz", "secret")

    assert identity is expected
    assert seeded.calls == [("admin@bank.uz", "secret")]
    assert ldap.calls == []


async def test_email_not_in_whitelist_uses_ldap() -> None:
    expected = _identity("ivanov@bank.uz")
    seeded = _Recorder(returns=None)
    ldap = _Recorder(returns=expected)
    adapter = BreakGlassAuthnAdapter(
        seeded=seeded,
        ldap=ldap,
        break_glass_emails=frozenset({"admin@bank.uz"}),
    )

    identity = await adapter.authenticate("ivanov@bank.uz", "secret")

    assert identity is expected
    assert seeded.calls == []
    assert ldap.calls == [("ivanov@bank.uz", "secret")]


async def test_email_match_is_case_insensitive() -> None:
    """LDAP/AD email'ы традиционно case-insensitive — whitelist тоже."""
    expected = _identity("admin@bank.uz")
    seeded = _Recorder(returns=expected)
    ldap = _Recorder(returns=None)
    adapter = BreakGlassAuthnAdapter(
        seeded=seeded,
        ldap=ldap,
        break_glass_emails=frozenset({"Admin@Bank.UZ"}),
    )

    identity = await adapter.authenticate("admin@bank.uz", "secret")

    assert identity is expected
    assert seeded.calls == [("admin@bank.uz", "secret")]


async def test_empty_whitelist_always_uses_ldap() -> None:
    expected = _identity("ivanov@bank.uz")
    seeded = _Recorder(returns=None)
    ldap = _Recorder(returns=expected)
    adapter = BreakGlassAuthnAdapter(
        seeded=seeded,
        ldap=ldap,
        break_glass_emails=frozenset(),
    )

    identity = await adapter.authenticate("ivanov@bank.uz", "secret")

    assert identity is expected
    assert seeded.calls == []
    assert ldap.calls == [("ivanov@bank.uz", "secret")]


def test_parse_break_glass_emails_empty() -> None:
    assert parse_break_glass_emails("") == frozenset()


def test_parse_break_glass_emails_strips_whitespace() -> None:
    assert parse_break_glass_emails("  a@b.uz , c@d.uz ") == frozenset(
        {"a@b.uz", "c@d.uz"}
    )


def test_parse_break_glass_emails_ignores_empty_tokens() -> None:
    assert parse_break_glass_emails("a@b.uz,,") == frozenset({"a@b.uz"})
