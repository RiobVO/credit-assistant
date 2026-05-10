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

    async def save(
        self,
        record: DossierRecord,
        snapshot_id: UUID,
        *,
        source_mode: str = "accountant",
        created_by_analyst_id: UUID | None = None,
    ) -> UUID:
        """Создаёт запись досье, привязанную к snapshot. Возвращает dossier id.

        ``source_mode`` определяет режим, в котором создано досье ('bank' |
        'accountant'). ``created_by_analyst_id`` обязателен в bank-mode и
        задаётся вызывающим use case'ом после ``get_current_analyst``.
        """
        ...

    async def get_by_id(self, dossier_id: UUID) -> DossierRecord | None: ...
