"""DossierRepositoryPort: контракт persistence для результата прогона правил."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from application.dto.dossier_record import DossierRecord
from application.ports.dossier_view_repository_port import DossierViewRepositoryPort


class DossierRepositoryPort(DossierViewRepositoryPort, Protocol):
    """Полный CRUD-интерфейс репо досье. Расширяет ``DossierViewRepositoryPort``
    (read-only ``get_view_by_id``), добавляя insert + точечное чтение записи.
    """

    async def save(self, record: DossierRecord, snapshot_id: UUID) -> UUID:
        """Создаёт запись досье, привязанную к snapshot. Возвращает dossier id."""
        ...

    async def get_by_id(self, dossier_id: UUID) -> DossierRecord | None: ...
