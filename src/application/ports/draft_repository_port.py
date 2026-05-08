"""DraftRepositoryPort: контракт persistence для черновиков формы.

Auth по знанию UUID — owner-поля нет (см. ADR 0005, появится в Phase 4).
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID


class DraftRepositoryPort(Protocol):
    async def create(self, payload: dict[str, Any]) -> UUID:
        """Создаёт черновик; expires_at = now() + draft_ttl_days. Возвращает id."""
        ...

    async def update(self, draft_id: UUID, payload: dict[str, Any]) -> bool:
        """Обновляет payload; продлевает expires_at. Возвращает True если найден."""
        ...

    async def get(self, draft_id: UUID) -> dict[str, Any] | None:
        """Возвращает payload; None если не найден или истёк."""
        ...

    async def purge_expired(self) -> int:
        """Удаляет все драфты с expires_at < now(). Возвращает кол-во удалённых."""
        ...
