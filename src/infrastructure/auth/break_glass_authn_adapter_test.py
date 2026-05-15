"""Unit-тесты BreakGlassAuthnAdapter."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from application.dto.analyst_identity import AnalystIdentity
from application.ports.authn_port import AuthnResult, AuthnSource
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


def _result(email: str, *, source: AuthnSource = "seeded") -> AuthnResult:
    return AuthnResult(identity=_identity(email), source=source)


class _Recorder:
    """Fake AuthnPort: запоминает вызовы + возвращает указанный result."""

    def __init__(self, returns: AuthnResult | None) -> None:
        self.returns = returns
        self.calls: list[tuple[str, str]] = []

    async def authenticate(
        self, email: str, password: str
    ) -> AuthnResult | None:
        self.calls.append((email, password))
        return self.returns


async def test_email_in_whitelist_uses_seeded_with_break_glass_source() -> None:
    seeded = _Recorder(returns=_result("admin@bank.uz", source="seeded"))
    ldap = _Recorder(returns=None)
    adapter = BreakGlassAuthnAdapter(
        seeded=seeded,
        ldap=ldap,
        break_glass_emails=frozenset({"admin@bank.uz"}),
    )

    result = await adapter.authenticate("admin@bank.uz", "secret")

    assert result is not None
    assert result.identity.email == "admin@bank.uz"
    # T1.5: source override — compliance audit подсветит как emergency-access.
    assert result.source == "break_glass"
    assert seeded.calls == [("admin@bank.uz", "secret")]
    assert ldap.calls == []


async def test_email_not_in_whitelist_uses_ldap() -> None:
    seeded = _Recorder(returns=None)
    ldap = _Recorder(returns=_result("ivanov@bank.uz", source="ldap"))
    adapter = BreakGlassAuthnAdapter(
        seeded=seeded,
        ldap=ldap,
        break_glass_emails=frozenset({"admin@bank.uz"}),
    )

    result = await adapter.authenticate("ivanov@bank.uz", "secret")

    assert result is not None
    assert result.source == "ldap"
    assert seeded.calls == []
    assert ldap.calls == [("ivanov@bank.uz", "secret")]


async def test_email_match_is_case_insensitive() -> None:
    """LDAP/AD email'ы традиционно case-insensitive — whitelist тоже."""
    seeded = _Recorder(returns=_result("admin@bank.uz", source="seeded"))
    ldap = _Recorder(returns=None)
    adapter = BreakGlassAuthnAdapter(
        seeded=seeded,
        ldap=ldap,
        break_glass_emails=frozenset({"Admin@Bank.UZ"}),
    )

    result = await adapter.authenticate("admin@bank.uz", "secret")

    assert result is not None
    assert result.source == "break_glass"
    assert seeded.calls == [("admin@bank.uz", "secret")]


async def test_empty_whitelist_always_uses_ldap() -> None:
    seeded = _Recorder(returns=None)
    ldap = _Recorder(returns=_result("ivanov@bank.uz", source="ldap"))
    adapter = BreakGlassAuthnAdapter(
        seeded=seeded,
        ldap=ldap,
        break_glass_emails=frozenset(),
    )

    result = await adapter.authenticate("ivanov@bank.uz", "secret")

    assert result is not None
    assert result.source == "ldap"
    assert seeded.calls == []
    assert ldap.calls == [("ivanov@bank.uz", "secret")]


async def test_break_glass_whitelist_but_wrong_password_returns_none() -> None:
    """Whitelist email + неверный пароль → None (без override на ldap)."""
    seeded = _Recorder(returns=None)
    ldap = _Recorder(returns=None)
    adapter = BreakGlassAuthnAdapter(
        seeded=seeded,
        ldap=ldap,
        break_glass_emails=frozenset({"admin@bank.uz"}),
    )

    result = await adapter.authenticate("admin@bank.uz", "wrong")

    assert result is None
    assert seeded.calls == [("admin@bank.uz", "wrong")]
    assert ldap.calls == []


def test_parse_break_glass_emails_empty() -> None:
    assert parse_break_glass_emails("") == frozenset()


def test_parse_break_glass_emails_strips_whitespace() -> None:
    assert parse_break_glass_emails("  a@b.uz , c@d.uz ") == frozenset(
        {"a@b.uz", "c@d.uz"}
    )


def test_parse_break_glass_emails_ignores_empty_tokens() -> None:
    assert parse_break_glass_emails("a@b.uz,,") == frozenset({"a@b.uz"})
