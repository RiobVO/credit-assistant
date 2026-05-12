"""T0.2 — usd_uzs_rates table for CBU API integration

Revision ID: e7b2a9d4f3c8
Revises: c4f8a1d3e0b2
Create Date: 2026-05-17 20:00:00.000000+00:00

Daily-granularity store для USD/UZS rate из CBU API (cbu.uz). Service-слой
читает DB-first → CBU live → DB cached → JSON bootstrap fallback chain.

``date`` PRIMARY KEY — один курс на банковский день (CBU обновляет 1×/день).
ON CONFLICT (date) DO NOTHING на save() обеспечивает конкурент-safe writes.

``Decimal(14,4)`` — широкий headroom для UZS-USD на десятилетия вперёд
(текущий ~12000, гиперинфляция × 100000 = 9.999.999.999,9999 верхний потолок).

``raw_response jsonb`` — оригинальный CBU JSON для аудита и forensics. На
~365 rows/год × ~250 bytes = ~100KB/год, retention 90+ дней — несущественно.

Index на ``date DESC`` ускоряет ``get_latest()`` lookup.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e7b2a9d4f3c8"
down_revision: str | None = "c4f8a1d3e0b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usd_uzs_rates",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("rate", sa.Numeric(14, 4), nullable=False),
        sa.Column("nominal", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("raw_response", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("date"),
    )
    op.create_index(
        "ix_usd_uzs_rates_date_desc",
        "usd_uzs_rates",
        [sa.text("date DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_usd_uzs_rates_date_desc", table_name="usd_uzs_rates")
    op.drop_table("usd_uzs_rates")
