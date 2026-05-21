"""ADR-0024 Session 3 — Borrower.oked_changed_by_owner для OKVED_CHANGED_12M narrow

Revision ID: c5e9d2a7b1f4
Revises: a7c1e4d8b3f5
Create Date: 2026-05-19 18:00:00.000000+00:00

ALTER TABLE borrowers ADD COLUMN oked_changed_by_owner BOOLEAN NOT NULL
DEFAULT false.

Заполнитель: правило OKVED_CHANGED_12M (Tier 2 backlog ADR-0024 — narrow scope)
теперь стреляет только когда смена ОКЭД помечена «по инициативе собственника»,
а не результат Госкомстат auto-overwrite. Default false для 49 existing
borrowers — все existing dossiers становятся silent для этого правила, что
ожидаемо (regression Commit 6 принимает диф).

Naming note: temporary mixed-prefix `oked_changed_by_owner` рядом с legacy
`oked_main_changed_at` существовал между Session 3 и Tier 3 rename. Полный
rename выполнен миграцией b04677374b85 (ПКМ РУз №275 от 24.08.2016).

Downgrade: DROP COLUMN.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c5e9d2a7b1f4"
down_revision = "a7c1e4d8b3f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "borrowers",
        sa.Column(
            "oked_changed_by_owner",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("borrowers", "oked_changed_by_owner")
