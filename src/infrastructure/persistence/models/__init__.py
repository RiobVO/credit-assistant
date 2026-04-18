"""ORM модели persistence слоя.

Импорт всех моделей здесь нужен, чтобы Alembic autogenerate видел их через
``Base.metadata`` (см. ``migrations/env.py``).
"""

from infrastructure.persistence.models.borrower import BorrowerORM
from infrastructure.persistence.models.borrower_snapshot import BorrowerSnapshotORM
from infrastructure.persistence.models.dossier import DossierORM
from infrastructure.persistence.models.draft import DraftORM

__all__ = [
    "BorrowerORM",
    "BorrowerSnapshotORM",
    "DossierORM",
    "DraftORM",
]
