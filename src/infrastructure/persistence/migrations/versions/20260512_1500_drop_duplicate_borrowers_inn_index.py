"""drop duplicate ix_borrowers_inn index (CA-006)

Revision ID: c4a8d1f37a91
Revises: 8f2a04c1b3e5
Create Date: 2026-05-12 15:00:00.000000+00:00

``UniqueConstraint("inn")`` уже создаёт ``borrowers_inn_key`` — отдельный
``ix_borrowers_inn`` был дублём и съедал место без выгоды. CA-006: убираем.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4a8d1f37a91"
down_revision: str | None = "8f2a04c1b3e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_borrowers_inn", table_name="borrowers")


def downgrade() -> None:
    op.create_index("ix_borrowers_inn", "borrowers", ["inn"], unique=False)
