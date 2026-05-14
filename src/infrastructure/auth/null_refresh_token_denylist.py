"""No-op denylist для dev без Redis (T1.2 / CA-019).

Активируется когда settings.redis_url is None. Сохраняет существующий
stateless 7-day refresh-режим: ничего не запоминаем, никого не отвергаем.

См. ADR-0016 «Refresh-token rotation».
"""

from __future__ import annotations

from datetime import datetime


class NullRefreshTokenDenylist:
    async def deny(self, jti: str, *, expires_at: datetime) -> bool:
        # «Успешно» — отсутствие denylist не должно блокировать rotation-flow.
        return True

    async def is_denied(self, jti: str) -> bool:
        return False
