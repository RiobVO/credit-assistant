"""DossierStorage: связка четырёх репозиториев под одной зависимостью.

Эндпоинту удобнее принимать одну DI-зависимость вместо четырёх. В тестах
`app.dependency_overrides[get_dossier_storage]` заменяется на in-memory dummy,
что позволяет проверять API-логику без поднятой БД (interaction-тесты с
настоящим Postgres — отдельная категория, появятся в 2.5.7 testcontainers).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.ports.borrower_repository_port import BorrowerRepositoryPort
from application.ports.borrower_snapshot_repository_port import (
    BorrowerSnapshotRepositoryPort,
)
from application.ports.dossier_repository_port import DossierRepositoryPort
from application.ports.draft_repository_port import DraftRepositoryPort
from infrastructure.persistence.database import get_session
from infrastructure.persistence.repositories.borrower_repository import (
    SqlAlchemyBorrowerRepository,
)
from infrastructure.persistence.repositories.borrower_snapshot_repository import (
    SqlAlchemyBorrowerSnapshotRepository,
)
from infrastructure.persistence.repositories.dossier_repository import (
    SqlAlchemyDossierRepository,
)
from infrastructure.persistence.repositories.draft_repository import (
    SqlAlchemyDraftRepository,
)


@dataclass(frozen=True, slots=True)
class DossierStorage:
    """Контейнер репозиториев. Все три hop'a досье + draft под одну сессию."""

    borrower: BorrowerRepositoryPort
    snapshot: BorrowerSnapshotRepositoryPort
    dossier: DossierRepositoryPort
    draft: DraftRepositoryPort


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_dossier_storage(session: SessionDep) -> DossierStorage:
    return DossierStorage(
        borrower=SqlAlchemyBorrowerRepository(session),
        snapshot=SqlAlchemyBorrowerSnapshotRepository(session),
        dossier=SqlAlchemyDossierRepository(session),
        draft=SqlAlchemyDraftRepository(session),
    )


# Reusable dependency annotation для эндпоинтов: импортируется в dossier.py / draft.py.
StorageDep = Annotated[DossierStorage, Depends(get_dossier_storage)]
