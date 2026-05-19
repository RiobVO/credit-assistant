"""ADR-0024 Tier 3 — rename Borrower.okved_main → oked_main per ПКМ РУз №275

Revision ID: b04677374b85
Revises: c5e9d2a7b1f4
Create Date: 2026-05-20 13:00:00.000000+00:00

ПКМ РУз №275 от 24.08.2016 устанавливает «ОКЭД» как официальный термин
для классификатора видов экономической деятельности РУз. Сессия 3 ADR-0024
ввела новое поле `oked_changed_by_owner` с явным префиксом ОКЭД, но оставила
legacy `okved_main` / `okved_main_changed_at` mixed-prefix temporary до этого
Tier 3 rename. Данная миграция закрывает rename.

ALTER TABLE borrowers RENAME COLUMN okved_main TO oked_main;
ALTER TABLE borrowers RENAME COLUMN okved_main_changed_at TO oked_main_changed_at;

49 existing borrowers — data preserved (Postgres ALTER COLUMN RENAME не
трогает значения, только метаданные столбца). JSONB payload в
`borrower_snapshots` / `drafts` не содержит borrower-поля
(см. snapshot_mapper.py:10) — backward-compat для JSONB не требуется.

Downgrade: reverse rename (oked_main → okved_main).
"""

from __future__ import annotations

from alembic import op

revision = "b04677374b85"
down_revision = "c5e9d2a7b1f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("borrowers", "okved_main", new_column_name="oked_main")
    op.alter_column(
        "borrowers", "okved_main_changed_at", new_column_name="oked_main_changed_at"
    )


def downgrade() -> None:
    op.alter_column(
        "borrowers", "oked_main_changed_at", new_column_name="okved_main_changed_at"
    )
    op.alter_column("borrowers", "oked_main", new_column_name="okved_main")
