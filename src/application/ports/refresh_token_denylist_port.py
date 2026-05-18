"""Protocol для refresh-token denylist (T1.2 / CA-019).

Используется при rotation на /refresh и при /logout — старый jti помечается
denied до его натурального exp. Decode на /refresh проверяет denylist и
отвергает запрос с 401 token_reused.

См. ADR-0016 «Refresh-token rotation» для контекста и trade-offs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class RefreshTokenDenylistPort(Protocol):
    async def deny(self, jti: str, *, expires_at: datetime) -> bool:
        """Атомарно добавить jti в denylist с TTL = expires_at - now.

        Returns:
            True — jti успешно denied (первый раз).
            False — jti уже был в denylist. Вызывающий должен трактовать как
            reuse-attack (параллельный refresh использовал тот же токен).
        """
        ...

    async def is_denied(self, jti: str) -> bool:
        """Проверить наличие jti в denylist. False — токен не denied."""
        ...
