"""Integration: RedisRefreshTokenDenylist против testcontainers redis.

Зеркало unit-test (fakeredis), но против реального Redis. Защищает от
семантических расхождений в SET NX EX между fakeredis 2.x и redis-py 7.x.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from testcontainers.redis import RedisContainer

from infrastructure.auth.redis_refresh_token_denylist import RedisRefreshTokenDenylist

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:
    with RedisContainer("redis:7-alpine") as container:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(6379))
        client: Redis = Redis(host=host, port=port, decode_responses=True)
        try:
            yield client
        finally:
            await client.aclose()


async def test_deny_then_is_denied_real_redis(redis_client: Redis) -> None:
    denylist = RedisRefreshTokenDenylist(redis_client, key_prefix="test:")
    expires = datetime.now(tz=UTC) + timedelta(seconds=60)
    assert await denylist.deny("jti-int", expires_at=expires) is True
    assert await denylist.is_denied("jti-int") is True


async def test_concurrent_deny_nx_winner_real_redis(redis_client: Redis) -> None:
    """Atomic SET NX EX: первый deny выигрывает, второй получает False."""
    denylist = RedisRefreshTokenDenylist(redis_client, key_prefix="test_race:")
    expires = datetime.now(tz=UTC) + timedelta(seconds=60)
    first = await denylist.deny("race-jti", expires_at=expires)
    second = await denylist.deny("race-jti", expires_at=expires)
    assert first is True
    assert second is False
