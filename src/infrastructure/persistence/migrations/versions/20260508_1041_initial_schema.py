"""initial schema

Revision ID: 1e51c05eab8c
Revises:
Create Date: 2026-05-08 10:41:17.437168+00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1e51c05eab8c"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "borrowers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("inn", sa.String(length=14), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("legal_form", sa.String(length=20), nullable=False),
        sa.Column("registration_date", sa.Date(), nullable=False),
        sa.Column("director_name", sa.String(length=255), nullable=False),
        sa.Column("director_appointed_at", sa.Date(), nullable=False),
        sa.Column("okved_main", sa.String(length=50), nullable=False),
        sa.Column("registered_address", sa.String(length=500), nullable=False),
        sa.Column("okved_main_changed_at", sa.Date(), nullable=True),
        sa.Column("charter_capital_amount", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("charter_capital_currency", sa.String(length=3), nullable=True),
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
        sa.UniqueConstraint("inn"),
    )
    op.create_index("ix_borrowers_inn", "borrowers", ["inn"], unique=False)
    op.create_table(
        "drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drafts_expires_at", "drafts", ["expires_at"], unique=False)
    op.create_table(
        "borrower_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("borrower_id", sa.UUID(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["borrower_id"], ["borrowers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_borrower_snapshots_borrower_id_as_of",
        "borrower_snapshots",
        ["borrower_id", "as_of"],
        unique=False,
    )
    op.create_table(
        "dossiers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("snapshot_id", sa.UUID(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("recommendation", sa.String(length=20), nullable=False),
        sa.Column("severity_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("red_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rules_version", sa.String(length=20), nullable=False),
        sa.Column("rules_evaluated", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["snapshot_id"], ["borrower_snapshots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dossiers_snapshot_id", "dossiers", ["snapshot_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dossiers_snapshot_id", table_name="dossiers")
    op.drop_table("dossiers")
    op.drop_index("ix_borrower_snapshots_borrower_id_as_of", table_name="borrower_snapshots")
    op.drop_table("borrower_snapshots")
    op.drop_index("ix_drafts_expires_at", table_name="drafts")
    op.drop_table("drafts")
    op.drop_index("ix_borrowers_inn", table_name="borrowers")
    op.drop_table("borrowers")
