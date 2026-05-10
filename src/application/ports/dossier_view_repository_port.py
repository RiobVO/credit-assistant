"""DossierViewRepositoryPort: контракт persistence для read-модели досье.

Read-only порт для GET /api/dossier/{id}. Имплементируется в
``SqlAlchemyDossierRepository.get_view_by_id`` одним SELECT с двумя JOIN.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from application.dto.dossier_view_record import DossierViewRecord


class DossierViewRepositoryPort(Protocol):
    async def get_view_by_id(self, dossier_id: UUID) -> DossierViewRecord | None: ...
