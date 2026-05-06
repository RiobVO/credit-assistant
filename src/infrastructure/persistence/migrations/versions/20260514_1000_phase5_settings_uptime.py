"""phase 5 — settings backend wiring + system_uptime_day

Revision ID: 7b3c5f08e2a1
Revises: c4a8d1f37a91
Create Date: 2026-05-14 10:00:00.000000+00:00

Добавляет колонки для Settings экрана + таблицу uptime-трекинга:

- ``analysts.password_changed_at`` (NOT NULL, default now()) — для UI-индикатора
  «пароль свежий — N дней». Backfill по existing analysts через server_default.
  Real-update произойдёт когда появится endpoint change-password (TODO[CA-068]).
- ``analysts.mfa_enabled`` (NOT NULL, default false) — флаг 2FA-enrollment'а.
  Заполняется seed-скриптом для admin@ как «enrolled in bank SSO/AD». Real
  TOTP/SMS enrollment-flow — отдельный эпик (TODO[CA-DS10]).
- ``system_uptime_day`` — append-only журнал дней-аптайма для UI-calendar
  «30 дней без сбоев». UPSERT'ится при каждом вызове GET /api/system/health,
  worst-of-day агрегация: 'ok' → 'degraded' → 'down'. Seed-row на today
  как стартовая точка для UI-rendering.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b3c5f08e2a1"
down_revision: str | None = "c4a8d1f37a91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysts",
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "analysts",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    op.create_table(
        "system_uptime_day",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="ok",
        ),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "worst_event_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "note",
            sa.String(length=255),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("day"),
    )

    # Seed row для today — стартовая точка UI-calendar'а.
    op.execute(
        "INSERT INTO system_uptime_day (day, status) "
        "VALUES (CURRENT_DATE, 'ok') ON CONFLICT (day) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("system_uptime_day")
    op.drop_column("analysts", "mfa_enabled")
    op.drop_column("analysts", "password_changed_at")
