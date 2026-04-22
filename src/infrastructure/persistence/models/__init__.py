"""ORM модели persistence слоя.

Импорт всех моделей здесь нужен, чтобы Alembic autogenerate видел их через
``Base.metadata`` (см. ``migrations/env.py``).
"""

from infrastructure.persistence.models.analyst import AnalystORM
from infrastructure.persistence.models.audit_log import AuditLogORM
from infrastructure.persistence.models.borrower import BorrowerORM
from infrastructure.persistence.models.borrower_snapshot import BorrowerSnapshotORM
from infrastructure.persistence.models.dossier import DossierORM
from infrastructure.persistence.models.draft import DraftORM

__all__ = [
    "AnalystORM",
    "AuditLogORM",
    "BorrowerORM",
    "BorrowerSnapshotORM",
    "DossierORM",
    "DraftORM",
]
