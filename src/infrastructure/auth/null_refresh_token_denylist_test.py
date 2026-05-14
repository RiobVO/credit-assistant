"""Unit для NullRefreshTokenDenylist — silent no-op fallback при REDIS_URL=None."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from infrastructure.auth.null_refresh_token_denylist import NullRefreshTokenDenylist


@pytest.mark.asyncio
async def test_null_denylist_deny_returns_true_and_never_raises() -> None:
    denylist = NullRefreshTokenDenylist()
    expires = datetime.now(tz=UTC) + timedelta(days=7)
    # Контракт deny: True означает «успешно добавили в denylist». Null-impl
    # возвращает True, чтобы caller не трактовал результат как reuse-attack.
    assert await denylist.deny("any-jti", expires_at=expires) is True


@pytest.mark.asyncio
async def test_null_denylist_is_denied_always_false() -> None:
    denylist = NullRefreshTokenDenylist()
    expires = datetime.now(tz=UTC) + timedelta(days=7)
    await denylist.deny("any-jti", expires_at=expires)
    assert await denylist.is_denied("any-jti") is False
    assert await denylist.is_denied("unknown") is False
