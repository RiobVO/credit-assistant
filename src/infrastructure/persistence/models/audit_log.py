"""ORM для AuditLog: append-only журнал действий банковских аналитиков.

Записывается из application use case'ов, не из endpoints. ИНН и др. PII в
``payload`` маскируются перед записью (Security Hard Rules в CLAUDE.md).
Никаких update/delete — только insert и select для отчётов.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.database import Base


class AuditLogORM(Base):
    """Append-only событие аудита."""

    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    # analyst_id nullable для неудачных логинов: системе ещё неизвестен analyst.
    analyst_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    event: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_audit_log_analyst_id_created_at", "analyst_id", "created_at"),
        Index("ix_audit_log_event_created_at", "event", "created_at"),
    )
