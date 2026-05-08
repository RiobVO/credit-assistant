"""BorrowerRepositoryPort: контракт persistence для заёмщика."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from domain.entities.borrower import Borrower
from domain.value_objects.inn import INN


class BorrowerRepositoryPort(Protocol):
    async def upsert(self, borrower: Borrower) -> UUID:
        """UPSERT по INN: создаёт или обновляет; возвращает persistence id.

        UUID — деталь persistence, но протекает в use case как ссылка для
        snapshot/dossier. Domain.Borrower по-прежнему не знает про id.
        """
        ...

    async def get_by_inn(self, inn: INN) -> Borrower | None: ...

    async def get_by_id(self, borrower_id: UUID) -> Borrower | None: ...
