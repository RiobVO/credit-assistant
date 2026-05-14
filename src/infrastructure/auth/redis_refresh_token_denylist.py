"""Redis-adapter для refresh-token denylist (T1.2 / CA-019).

Контракт: `<key_prefix><jti>` → "1" с TTL = max(1, expires_at - now) секунд.
Атомарный SET NX EX: при NX=False ключ уже существует → второй параллельный
refresh обнаружил denied jti, caller трактует как reuse-attack.

Fail-mode: `redis.exceptions.ConnectionError` / `TimeoutError` всплывают
наверх — caller (auth.py /refresh) должен поймать и вернуть 503/401 (fail
closed), чтобы compromised tokens не проскочили при недоступности Redis.

См. ADR-0016 «Refresh-token rotation».
"""

from __future__ import annotations

from datetime import UTC, datetime

from redis.asyncio import Redis


class RedisRefreshTokenDenylist:
    def __init__(self, client: Redis, *, key_prefix: str = "refresh_denylist:") -> None:
        self._client = client
        self._prefix = key_prefix

    async def deny(self, jti: str, *, expires_at: datetime) -> bool:
        # TTL clamp до 1s — Redis отвергает EX<=0 (ValueError). Прошедший
        # expires_at означает clock-skew между issue и rotation; денилист
        # должен принять запрос (ключ ещё не expired у адаптера), кратко
        # хранит и сам истекает.
        ttl_seconds = max(1, int((expires_at - datetime.now(tz=UTC)).total_seconds()))
        # SET NX EX: True если ключ был создан, None если уже существовал.
        result = await self._client.set(
            self._key(jti), "1", nx=True, ex=ttl_seconds
        )
        return result is True

    async def is_denied(self, jti: str) -> bool:
        # redis-py типизирует EXISTS как Any; явно приводим к int → bool.
        count: int = await self._client.exists(self._key(jti))
        return count > 0

    def _key(self, jti: str) -> str:
        return f"{self._prefix}{jti}"
