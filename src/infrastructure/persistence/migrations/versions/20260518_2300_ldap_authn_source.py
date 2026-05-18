"""T1.5.2 — analysts.password_hash nullable + authn_source (ADR-0019)

Revision ID: f4a2d6c9e3b8
Revises: e7f9a3c2b8d1
Create Date: 2026-05-18 23:00:00.000000+00:00

(1) ALTER COLUMN analysts.password_hash DROP NOT NULL — LDAP-provisioned
    users держат password_hash = NULL (LDAP-server владеет паролями).
(2) ADD COLUMN analysts.authn_source VARCHAR(20) NOT NULL DEFAULT 'seeded'
    + CHECK constraint (seeded | ldap).

Existing rows: authn_source='seeded' default → совместимо. Seeded users
сохраняют password_hash; LDAP users (после T1.5.2 upsert flow) пишут
password_hash=NULL.

Downgrade осторожный:
- Если в БД есть rows с password_hash IS NULL и authn_source='ldap',
  upgrade обратно к NOT NULL уронит миграцию. Downgrade сначала ставит
  placeholder password_hash='' (заведомо invalid bcrypt) для таких rows,
  потом restore NOT NULL. Это нужно для возможности re-apply миграции;
  потерянные данные = 0 (LDAP users всё равно проходят через LDAP).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f4a2d6c9e3b8"
down_revision = "e7f9a3c2b8d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "analysts",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.add_column(
        "analysts",
        sa.Column(
            "authn_source",
            sa.String(length=20),
            nullable=False,
            server_default="seeded",
        ),
    )
    op.create_check_constraint(
        "ck_analysts_authn_source",
        "analysts",
        "authn_source IN ('seeded', 'ldap')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_analysts_authn_source", "analysts", type_="check")
    op.drop_column("analysts", "authn_source")
    # Перед NOT NULL restore — backfill для LDAP rows (если есть).
    op.execute(
        "UPDATE analysts SET password_hash = '' WHERE password_hash IS NULL"
    )
    op.alter_column(
        "analysts",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=False,
    )
