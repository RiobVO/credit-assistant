"""DossierRepositoryPort: контракт persistence для результата прогона правил."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from application.dto.dossier_record import DossierRecord


class DossierRepositoryPort(Protocol):
    async def save(self, record: DossierRecord, snapshot_id: UUID) -> UUID:
        """Создаёт запись досье, привязанную к snapshot. Возвращает dossier id."""
        ...

    async def get_by_id(self, dossier_id: UUID) -> DossierRecord | None: ...
