"""T1.4.2 — audit_log.brand_id для forensics (ADR-0018)

Revision ID: e7f9a3c2b8d1
Revises: c5d2f3a7e1b4
Create Date: 2026-05-18 22:00:00.000000+00:00

ALTER TABLE audit_log ADD COLUMN brand_id VARCHAR(50) NOT NULL DEFAULT 'default'.
Backfill 'default' для existing rows (де-факто single-tenant до T1.4).

Forensics use-case: SQL `SELECT DISTINCT brand_id FROM audit_log WHERE
created_at > now() - interval '24h'` обнаруживает cross-contamination
postfactum, если оператор подключил API одного банка к чужой БД.

Downgrade: DROP COLUMN + DROP INDEX.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e7f9a3c2b8d1"
down_revision = "c5d2f3a7e1b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_log",
        sa.Column(
            "brand_id",
            sa.String(length=50),
            nullable=False,
            server_default="default",
        ),
    )
    op.create_index(
        "ix_audit_log_brand_id_created_at",
        "audit_log",
        ["brand_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_brand_id_created_at", table_name="audit_log")
    op.drop_column("audit_log", "brand_id")
