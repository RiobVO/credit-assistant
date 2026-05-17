"""T3.2.4 — audit_log.request_id для correlation_id forensics

Revision ID: a7c1e4d8b3f5
Revises: f4a2d6c9e3b8
Create Date: 2026-05-18 24:00:00.000000+00:00

ALTER TABLE audit_log ADD COLUMN request_id VARCHAR(32) NULL + index.
Nullable: записи аудита, эмитированные **вне** HTTP-цикла (CLI, jobs,
background-tasks без middleware), пишутся без request_id.

Forensics use-case: при инциденте оператор знает X-Request-ID (из support
ticket / Sentry tag / browser DevTools) — SQL ``SELECT * FROM audit_log
WHERE request_id = 'xxx'`` дотягивает полный сюжет действий.

Downgrade: DROP INDEX → DROP COLUMN.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a7c1e4d8b3f5"
down_revision = "f4a2d6c9e3b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_log",
        sa.Column("request_id", sa.String(length=32), nullable=True),
    )
    op.create_index(
        "ix_audit_log_request_id",
        "audit_log",
        ["request_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_request_id", table_name="audit_log")
    op.drop_column("audit_log", "request_id")
