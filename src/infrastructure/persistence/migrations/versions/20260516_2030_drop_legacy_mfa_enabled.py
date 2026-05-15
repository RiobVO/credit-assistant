"""CA-DS16 — drop legacy analysts.mfa_enabled stored bool

Revision ID: c4f8a1d3e0b2
Revises: 9a4d2e1f8b67
Create Date: 2026-05-16 20:30:00.000000+00:00

Phase 5.A добавила ``analysts.mfa_enabled`` как stored bool для отметки
аналитика «enrolled в банковский SSO/AD». Phase 5.B (миграция
9a4d2e1f8b67) ввела real TOTP enrollment через ``mfa_enrolled_at``;
с этого момента API computed ``mfa_enabled = mfa_enrolled_at IS NOT NULL``
(см. analyst_mapper.py), а stored bool остался как dead-storage —
ставился /enroll/verify и /disable + admin/reset, но никто не читал.

CA-DS16 чистит этот рудимент:
- Drop column ``analysts.mfa_enabled``.
- ``AnalystORM``, ``analyst_repository.add``, ``seed_analysts.py``
  больше не упоминают field.
- API контракт ``AnalystIdentity.mfa_enabled`` (computed) и
  ``LoginResponse.mfa_enabled`` остаются — frontend читает без изменений.

Backward-compat: downgrade воссоздаёт колонку с default false +
backfill из ``mfa_enrolled_at IS NOT NULL`` — старая stored семантика
восстанавливается ровно из того же source-of-truth, который сейчас.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f8a1d3e0b2"
down_revision: str | None = "9a4d2e1f8b67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("analysts", "mfa_enabled")


def downgrade() -> None:
    op.add_column(
        "analysts",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Backfill: всё ещё-enrolled аналитики получают True, остальные False.
    op.execute(
        "UPDATE analysts SET mfa_enabled = TRUE "
        "WHERE mfa_enrolled_at IS NOT NULL"
    )
    # Снимаем server_default — semantic stored bool, а не auto-fill.
    op.alter_column("analysts", "mfa_enabled", server_default=None)
