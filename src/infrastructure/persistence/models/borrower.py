"""ORM для Borrower: нормализованная таблица заёмщиков с уникальным INN.

Поля 1:1 с ``domain.entities.Borrower`` плюс audit-колонки. Money разложен
на ``amount`` + ``currency`` (обратное склеивание — в mapper в 2.5.4).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.database import Base
from infrastructure.persistence.types.encrypted_string import EncryptedString


class BorrowerORM(Base):
    """Заёмщик. Уникален по INN — переиспользуется между прогонами."""

    __tablename__ = "borrowers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    inn: Mapped[str] = mapped_column(String(14), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_form: Mapped[str] = mapped_column(String(20), nullable=False)
    registration_date: Mapped[date] = mapped_column(nullable=False)
    # T1.3 (ADR-0017): director_name — PII физлица, шифруется через Fernet.
    # Length 500 для Fernet token (255 plaintext → ~432 base64 chars).
    director_name: Mapped[str] = mapped_column(EncryptedString(500), nullable=False)
    director_appointed_at: Mapped[date] = mapped_column(nullable=False)
    oked_main: Mapped[str] = mapped_column(String(50), nullable=False)
    registered_address: Mapped[str] = mapped_column(String(500), nullable=False)
    oked_main_changed_at: Mapped[date | None] = mapped_column(nullable=True)
    # ADR-0024 Session 3: narrow для OKVED_CHANGED_12M (см. domain
    # `Borrower.oked_changed_by_owner` docstring). NOT NULL DEFAULT false —
    # 49 existing borrowers получают false через миграцию c5e9d2a7b1f4.
    oked_changed_by_owner: Mapped[bool] = mapped_column(
        Boolean(),
        nullable=False,
        server_default="false",
    )

    charter_capital_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    charter_capital_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
