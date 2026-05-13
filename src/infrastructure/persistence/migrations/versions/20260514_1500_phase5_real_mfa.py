"""phase 5 — real TOTP 2FA columns

Revision ID: 9a4d2e1f8b67
Revises: 7b3c5f08e2a1
Create Date: 2026-05-14 15:00:00.000000+00:00

Добавляет три nullable колонки для real TOTP enrollment + backup-codes
support. Не трогает существующий ``mfa_enabled`` — после этого PR он
становится computed-from-secret (см. analyst_mapper.py): нет secret →
mfa_enabled=False в API, даже если stored bool=True. Это сжигает прежний
security-theater seed для admin@.

- ``mfa_secret`` — base32-encoded TOTP shared secret (RFC 6238). Хранится
  plain в БД, поскольку POC. Production должен encrypt через банковский
  vault/KMS (TODO[CA-DS12]). NULL = MFA не настроен.
- ``mfa_enrolled_at`` — момент успешной первой verify-проверки. NULL до
  enrollment'а.
- ``mfa_backup_codes_hash`` — JSON-массив bcrypt-хешей одноразовых
  recovery-кодов. По умолчанию 10 штук генерится при enrollment'е,
  каждый используется один раз и сжигается. NULL = ещё не сгенерированы.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9a4d2e1f8b67"
down_revision: str | None = "7b3c5f08e2a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysts",
        sa.Column("mfa_secret", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "analysts",
        sa.Column(
            "mfa_enrolled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "analysts",
        sa.Column(
            "mfa_backup_codes_hash",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("analysts", "mfa_backup_codes_hash")
    op.drop_column("analysts", "mfa_enrolled_at")
    op.drop_column("analysts", "mfa_secret")
