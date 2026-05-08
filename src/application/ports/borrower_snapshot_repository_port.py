"""BorrowerSnapshotRepositoryPort: контракт persistence для immutable snapshot."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from domain.entities.borrower_snapshot import BorrowerSnapshot


class BorrowerSnapshotRepositoryPort(Protocol):
    async def save(self, snapshot: BorrowerSnapshot, borrower_id: UUID) -> UUID:
        """Создаёт новую запись snapshot. Snapshot иммутабелен — update не предусмотрен."""
        ...

    async def get_by_id(self, snapshot_id: UUID) -> BorrowerSnapshot | None: ...
