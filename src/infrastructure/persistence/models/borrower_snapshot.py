"""ORM для BorrowerSnapshot: immutable артефакт прогона.

Хранит весь snapshot целиком в JSONB. Нормализация не выгодна:
правила всегда читают snapshot целиком, query внутри payload не предполагается.
Decimal сериализуется как str, date — как ISO; конкретные mappers — в 2.5.4.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.database import Base
from infrastructure.persistence.types.encrypted_jsonb import EncryptedJsonb


class BorrowerSnapshotORM(Base):
    """Снимок данных заёмщика на дату ``as_of``. Иммутабелен."""

    __tablename__ = "borrower_snapshots"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    borrower_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("borrowers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    as_of: Mapped[date] = mapped_column(nullable=False)

    # Полный сериализованный BorrowerSnapshot (без вложенного Borrower —
    # тот достаётся join-ом по borrower_id).
    # T1.3 (ADR-0017): шифруется через EncryptedJsonb — wrap pattern
    # {"_encrypted": true, "ciphertext": "..."}. Тип колонки остаётся JSONB.
    payload: Mapped[dict[str, Any]] = mapped_column(EncryptedJsonb, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_borrower_snapshots_borrower_id_as_of", "borrower_id", "as_of"),
    )
