"""ORM для Draft: незаконченный ввод формы Manual Input.

Хранит сырой JSON payload (структура частичная — UI шлёт по шагам).
``expires_at`` ставится в коде при insert/update: ``now() + draft_ttl_days``;
purge — отдельной задачей в Phase 2.5.6+.

Auth модели здесь нет: владелец draft'а определяется владением UUID-ссылки.
В Phase 4 (Bank Mode) добавится ``owner_user_id``. См. ADR 0005.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.database import Base
from infrastructure.persistence.types.encrypted_jsonb import EncryptedJsonb


class DraftORM(Base):
    """Черновик формы. Уникален по UUID, без owner — auth по знанию ссылки."""

    __tablename__ = "drafts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    # T1.3 (ADR-0017): manual-input payload содержит PII (director_name,
    # счета контрагентов). EncryptedJsonb wrap pattern. TTL 30d.
    payload: Mapped[dict[str, Any]] = mapped_column(EncryptedJsonb, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_drafts_expires_at", "expires_at"),)
