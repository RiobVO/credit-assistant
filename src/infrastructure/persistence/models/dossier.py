"""ORM для Dossier: результат прогона правил поверх snapshot.

``score`` / ``recommendation`` нормализованы — по ним строится листинг и фильтрация.
``red_flags`` и ``severity_breakdown`` хранятся в JSONB: их форма меняется
вместе с rules engine, и они всегда читаются целиком.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.database import Base


class DossierORM(Base):
    """Результат красно-флагового прогона. 1:1 со snapshot."""

    __tablename__ = "dossiers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("borrower_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )

    score: Mapped[int] = mapped_column(Integer, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False)
    severity_breakdown: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False)
    red_flags: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)

    rules_version: Mapped[str] = mapped_column(String(20), nullable=False)
    rules_evaluated: Mapped[int] = mapped_column(Integer, nullable=False)

    # T1.1: banking-grade monotonic case_id `BR-YYYY-NNNN`. Аллоцируется
    # `CaseIdAllocator`'ом per-year через Postgres SEQUENCE + advisory lock.
    # UNIQUE через миграцию (`uq_dossiers_case_id`), не на колонке —
    # alembic source of truth.
    case_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

    # Phase 4: разделение по режиму создания + аудит-trail на аналитика.
    # source_mode='accountant' для всех записей до Phase 4 (backfill в миграции).
    # created_by_analyst_id null для accountant-mode и legacy записей.
    source_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="accountant"
    )
    created_by_analyst_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysts.id", ondelete="RESTRICT"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_dossiers_snapshot_id", "snapshot_id"),
        Index("ix_dossiers_source_mode_created_at", "source_mode", "created_at"),
        Index("ix_dossiers_created_by_analyst_id", "created_by_analyst_id"),
    )
