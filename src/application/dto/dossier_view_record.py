"""DossierViewRecord: read-модель для GET /api/dossier/{id}.

Собирает в одну запись три источника, которые нужны экрану досье:

* ``dossier_id`` + ``created_at`` — из таблицы ``dossiers`` (id результата
  прогона, дата записи);
* ``dossier`` (``DossierRecord``) — score, recommendation, red flags;
* ``snapshot`` (``BorrowerSnapshot``) — все исходные данные, на которых
  считались правила; ``snapshot.borrower`` уже содержит реквизиты заёмщика,
  отдельным полем не дублируем.

Read-only DTO: никто его не пишет, заполняется репо за один SELECT с двумя
JOIN (см. ``SqlAlchemyDossierRepository.get_view_by_id``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from application.dto.dossier_record import DossierRecord
from domain.entities.borrower_snapshot import BorrowerSnapshot


@dataclass(frozen=True, slots=True)
class DossierViewRecord:
    dossier_id: UUID
    dossier: DossierRecord
    snapshot: BorrowerSnapshot
    created_at: datetime
