"""ORM для gnk_certificates: справки ГНК с manual upload (T0.3 Phase A).

File-storage: ``file_bytes BYTEA`` внутри row — backup-friendly, atomic с
metadata. Phase B (CA-DS28) добавит ``source="gnk_live"`` без schema changes.

PK = UUID (auto-generated, history-friendly: одна фирма может иметь N
загруженных справок за время). Latest резолвится через ``uploaded_at DESC``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.database import Base


class GnkCertificateORM(Base):
    __tablename__ = "gnk_certificates"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    borrower_inn: Mapped[str] = mapped_column(String(14), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    okveds: Mapped[list[str]] = mapped_column(
        ARRAY(String(10)), nullable=False, default=list
    )
    cert_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    file_bytes: Mapped[bytes | None] = mapped_column(BYTEA, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    uploaded_by_analyst_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("analysts.id", ondelete="SET NULL"),
        nullable=True,
    )
