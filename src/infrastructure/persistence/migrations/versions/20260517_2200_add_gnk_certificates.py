"""T0.3 — gnk_certificates table for manual upload (Phase A)

Revision ID: a1f3c5e8b9d2
Revises: e7b2a9d4f3c8
Create Date: 2026-05-17 22:00:00.000000+00:00

Phase A: аналитик грузит PDF/JPG справки + ручной ввод полей (full_name,
status, okveds, optional cert_id). Phase B (CA-DS28) добавит ``source =
"gnk_live"`` после automatic fetch — schema готова для этого.

File storage: ``file_bytes BYTEA`` внутри row — backup-friendly (pg_dump
покрывает всё), atomic transaction с metadata, нет volume mount. Pattern
mirror ADR-0014 (raw_response jsonb в usd_uzs_rates) для аудита.

``borrower_inn`` not FK к borrowers.inn (borrowers создаются draft-step1 после
upload; справку можно класть и без созданного borrower-row). Index на
borrower_inn для быстрого ``get_latest_for_inn``.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1f3c5e8b9d2"
down_revision: str | None = "e7b2a9d4f3c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gnk_certificates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("borrower_inn", sa.String(14), nullable=False),
        sa.Column("full_name", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "okveds",
            postgresql.ARRAY(sa.String(10)),
            nullable=False,
            server_default=sa.text("ARRAY[]::VARCHAR(10)[]"),
        ),
        sa.Column("cert_id", sa.String(50), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default=sa.text("'uploaded'")),
        sa.Column("file_bytes", postgresql.BYTEA(), nullable=True),
        sa.Column("mime_type", sa.String(50), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by_analyst_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_gnk_certificates_borrower_inn_uploaded_at",
        "gnk_certificates",
        ["borrower_inn", sa.text("uploaded_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_gnk_certificates_borrower_inn_uploaded_at",
        table_name="gnk_certificates",
    )
    op.drop_table("gnk_certificates")
