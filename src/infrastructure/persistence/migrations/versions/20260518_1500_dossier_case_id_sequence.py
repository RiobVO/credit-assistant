"""T1.1 — dossier_case_id sequence (compromised B)

Revision ID: b3e9f1a7d4c5
Revises: a1f3c5e8b9d2
Create Date: 2026-05-18 15:00:00.000000+00:00

Заменяет derived BR-YYYY-XXXX (от UUID first-4-hex) на monotonic sequence
per-year. Backfill: existing dossiers нумеруются ASC по created_at в их
году (ROW_NUMBER() OVER PARTITION BY year). После backfill setval'им
sequence на MAX seq текущего года + 1, чтобы первый allocate после
миграции взял MAX+1.

Format: BR-{YYYY}-{NNNN} (4 цифры zfill). UNIQUE constraint глобальный
(не per-year) — sequence гарантирует отсутствие коллизий, UNIQUE — defence
in depth и FK-target в будущем (Phase 4 applications).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e9f1a7d4c5"
down_revision: str | None = "a1f3c5e8b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS dossier_case_seq START WITH 1")

    op.add_column(
        "dossiers",
        sa.Column("case_id", sa.String(20), nullable=True),
    )

    # Backfill per-year ASC по created_at. ROW_NUMBER даёт monotonic
    # nnnn в пределах года, tiebreaker по id для детерминизма при
    # совпадающем created_at.
    op.execute(
        """
        WITH numbered AS (
            SELECT id,
                   EXTRACT(YEAR FROM created_at)::int AS yr,
                   ROW_NUMBER() OVER (
                       PARTITION BY EXTRACT(YEAR FROM created_at)
                       ORDER BY created_at, id
                   ) AS rn
            FROM dossiers
        )
        UPDATE dossiers d
        SET case_id = 'BR-' || numbered.yr::text || '-'
                      || LPAD(numbered.rn::text, 4, '0')
        FROM numbered
        WHERE d.id = numbered.id
        """
    )

    op.alter_column("dossiers", "case_id", nullable=False)
    op.create_unique_constraint("uq_dossiers_case_id", "dossiers", ["case_id"])
    op.create_index("ix_dossiers_case_id", "dossiers", ["case_id"])

    # Setval sequence на MAX seq текущего года + 1. is_called=false →
    # next nextval вернёт переданное значение. Если current-year rows нет —
    # next nextval = 1.
    op.execute(
        """
        SELECT setval(
            'dossier_case_seq',
            GREATEST(1, COALESCE((
                SELECT MAX(SUBSTRING(case_id FROM 9 FOR 4)::int) + 1
                FROM dossiers
                WHERE SUBSTRING(case_id FROM 4 FOR 4)::int
                      = EXTRACT(YEAR FROM CURRENT_DATE)::int
            ), 1)),
            false
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_dossiers_case_id", table_name="dossiers")
    op.drop_constraint("uq_dossiers_case_id", "dossiers", type_="unique")
    op.drop_column("dossiers", "case_id")
    op.execute("DROP SEQUENCE IF EXISTS dossier_case_seq")
