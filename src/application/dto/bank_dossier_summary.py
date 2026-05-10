"""DTO для bank-mode read-моделей: search-результат и пагинированный list."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BorrowerSearchHit:
    """Результат `GET /api/bank/borrowers/search?inn=...`.

    ``found`` отделяет «borrower есть в БД» от «borrower есть и у него bank-mode
    досье». UI выбирает между «Открыть» / «Загрузить выгрузки» по ``dossier_id``.
    """

    found: bool
    borrower_id: UUID | None
    borrower_name: str | None
    dossier_id: UUID | None
    score: int | None
    created_at: datetime | None


@dataclass(frozen=True, slots=True)
class BankDossierListItem:
    """Строка в `GET /api/bank/dossiers` (история).

    ``analyst_full_name`` опционален: для accountant-mode (если когда-то
    смешается на одной инсталляции) и для legacy-записей без аналитика — None.
    На bank install все записи будут иметь имя.
    """

    dossier_id: UUID
    inn: str
    borrower_name: str
    score: int
    recommendation: str
    created_at: datetime
    analyst_id: UUID | None
    analyst_full_name: str | None


@dataclass(frozen=True, slots=True)
class BankDossierListPage:
    items: tuple[BankDossierListItem, ...]
    total: int
    page: int
    page_size: int
