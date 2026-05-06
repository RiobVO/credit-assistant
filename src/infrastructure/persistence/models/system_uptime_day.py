"""ORM для system_uptime_day: append-only журнал дней аптайма.

Запись UPSERT'ится при каждом вызове GET /api/system/health: если today-row
существует — last_seen_at обновляется + status пересчитывается worst-of-day
(ok → degraded → down). Если нет — создаётся 'ok' и first_seen_at=now().

UI Settings → «О системе» рендерит calendar 30 квадратов из последних 30 записей.
Дни до самого первого row'а (первый день деплоя) — grey «до запуска».
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.persistence.database import Base


class SystemUptimeDayORM(Base):
    """Один календарный день = один row. PK = day."""

    __tablename__ = "system_uptime_day"

    day: Mapped[date_type] = mapped_column(Date, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    worst_event_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
