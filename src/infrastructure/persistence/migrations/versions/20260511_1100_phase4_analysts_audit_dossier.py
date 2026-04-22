"""phase 4 — analysts, audit_log, dossier auth columns

Revision ID: 8f2a04c1b3e5
Revises: 1e51c05eab8c
Create Date: 2026-05-11 11:00:00.000000+00:00

Добавляет seeded auth (``analysts``), append-only audit (``audit_log``) и
два колонки в ``dossiers`` для разделения режимов и аудита создателя:

- ``dossiers.source_mode`` (NOT NULL, default 'accountant') — режим, в котором
  создано досье. Backfill всех существующих в 'accountant' через server_default.
- ``dossiers.created_by_analyst_id`` (nullable FK → analysts) — кто из аналитиков
  сгенерировал. NULL для accountant-mode и legacy записей.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8f2a04c1b3e5"
down_revision: str | None = "1e51c05eab8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("analyst_id", sa.UUID(), nullable=True),
        sa.Column("event", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.UUID(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["analyst_id"], ["analysts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_log_analyst_id_created_at",
        "audit_log",
        ["analyst_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_log_event_created_at",
        "audit_log",
        ["event", "created_at"],
        unique=False,
    )

    op.add_column(
        "dossiers",
        sa.Column(
            "source_mode",
            sa.String(length=20),
            nullable=False,
            server_default="accountant",
        ),
    )
    op.add_column(
        "dossiers",
        sa.Column("created_by_analyst_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_dossiers_created_by_analyst_id",
        "dossiers",
        "analysts",
        ["created_by_analyst_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_dossiers_source_mode_created_at",
        "dossiers",
        ["source_mode", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_dossiers_created_by_analyst_id",
        "dossiers",
        ["created_by_analyst_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dossiers_created_by_analyst_id", table_name="dossiers")
    op.drop_index("ix_dossiers_source_mode_created_at", table_name="dossiers")
    op.drop_constraint(
        "fk_dossiers_created_by_analyst_id", "dossiers", type_="foreignkey"
    )
    op.drop_column("dossiers", "created_by_analyst_id")
    op.drop_column("dossiers", "source_mode")

    op.drop_index("ix_audit_log_event_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_analyst_id_created_at", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_table("analysts")
