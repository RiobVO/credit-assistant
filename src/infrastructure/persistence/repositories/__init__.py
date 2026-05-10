"""SQLAlchemy-импл репозиториев — реализуют Protocol-порты из application/."""

from infrastructure.persistence.repositories.analyst_repository import (
    SqlAlchemyAnalystRepository,
)
from infrastructure.persistence.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
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

__all__ = [
    "SqlAlchemyAnalystRepository",
    "SqlAlchemyAuditLogRepository",
    "SqlAlchemyBorrowerRepository",
    "SqlAlchemyBorrowerSnapshotRepository",
    "SqlAlchemyDossierRepository",
    "SqlAlchemyDraftRepository",
]
