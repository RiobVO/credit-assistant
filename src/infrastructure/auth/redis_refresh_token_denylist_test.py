"""Unit для RedisRefreshTokenDenylist через fakeredis (T1.2 / CA-019).

Покрытие:
- deny() первый вызов → True, ключ присутствует с правильным TTL.
- deny() повторный вызов того же jti → False (NX race-detection).
- is_denied(): True для denied, False для unknown.
- TTL clamp: прошедший expires_at → adapter clamps до 1s, не падает.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import fakeredis.aioredis
import pytest

from infrastructure.auth.redis_refresh_token_denylist import RedisRefreshTokenDenylist


@pytest.fixture
def fake_redis() -> fakeredis.aioredis.FakeRedis:
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def denylist(
    fake_redis: fakeredis.aioredis.FakeRedis,
) -> RedisRefreshTokenDenylist:
    return RedisRefreshTokenDenylist(fake_redis, key_prefix="refresh_denylist:")


@pytest.mark.asyncio
async def test_deny_first_call_returns_true_and_records_key(
    denylist: RedisRefreshTokenDenylist,
    fake_redis: fakeredis.aioredis.FakeRedis,
) -> None:
    expires = datetime.now(tz=UTC) + timedelta(seconds=60)
    assert await denylist.deny("jti-1", expires_at=expires) is True
    assert await fake_redis.exists("refresh_denylist:jti-1") == 1


@pytest.mark.asyncio
async def test_deny_second_call_returns_false_nx_race_detection(
    denylist: RedisRefreshTokenDenylist,
) -> None:
    expires = datetime.now(tz=UTC) + timedelta(seconds=60)
    await denylist.deny("jti-1", expires_at=expires)
    # Второй deny того же jti — NX вернёт None, adapter возвращает False.
    assert await denylist.deny("jti-1", expires_at=expires) is False


@pytest.mark.asyncio
async def test_is_denied_true_after_deny(denylist: RedisRefreshTokenDenylist) -> None:
    expires = datetime.now(tz=UTC) + timedelta(seconds=60)
    await denylist.deny("jti-2", expires_at=expires)
    assert await denylist.is_denied("jti-2") is True


@pytest.mark.asyncio
async def test_is_denied_false_for_unknown(
    denylist: RedisRefreshTokenDenylist,
) -> None:
    assert await denylist.is_denied("ghost") is False


@pytest.mark.asyncio
async def test_ttl_matches_expires_at_minus_now(
    denylist: RedisRefreshTokenDenylist,
    fake_redis: fakeredis.aioredis.FakeRedis,
) -> None:
    expires = datetime.now(tz=UTC) + timedelta(seconds=120)
    await denylist.deny("jti-ttl", expires_at=expires)
    ttl = await fake_redis.ttl("refresh_denylist:jti-ttl")
    # Допуск ±2s для clock-drift между измерением и SET.
    assert 118 <= ttl <= 120


@pytest.mark.asyncio
async def test_past_expires_clamps_to_min_ttl(
    denylist: RedisRefreshTokenDenylist,
    fake_redis: fakeredis.aioredis.FakeRedis,
) -> None:
    """Если expires уже прошёл — Redis отвергнет EX<=0. Adapter clamps до 1s.

    После clamp ключ существует с TTL=1, через секунду истечёт натурально.
    """
    expires = datetime.now(tz=UTC) - timedelta(seconds=10)
    assert await denylist.deny("jti-past", expires_at=expires) is True
    ttl = await fake_redis.ttl("refresh_denylist:jti-past")
    # 1s clamp; race-condition: может уже expire'нуться (-2) если тест медленный.
    assert ttl in (1, -2)
