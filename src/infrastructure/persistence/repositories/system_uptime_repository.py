"""SqlAlchemySystemUptimeRepository: UPSERT today + list-last-N для uptime-calendar.

Worst-of-day агрегация: внутри одного календарного дня status может только
эскалироваться (ok → degraded → down), не deeskalироваться. ``worst_event_at``
ставится в момент эскалации — для будущего alert/audit-flow.

Read возвращает ORM-объекты — это инфраструктурный repo для thin endpoint,
выше его в чистый domain ничего не идёт.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.models.system_uptime_day import SystemUptimeDayORM

# Ранжирование severity. INSERT при INSERT-OR-NOTHING (status='ok' default),
# в UPDATE-ветке status поднимается до GREATEST(старый, новый).
_SEVERITY: dict[str, int] = {"ok": 0, "degraded": 1, "down": 2}


class SqlAlchemySystemUptimeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_today(
        self,
        *,
        status: str,
        note: str | None = None,
        today: date_type | None = None,
        now: datetime | None = None,
    ) -> SystemUptimeDayORM:
        """UPSERT записи на сегодня. Если row нет — создаёт с этим статусом.
        Если есть — обновляет last_seen_at, эскалирует status если нужно.

        ``today`` / ``now`` можно инжектировать для детерминированных тестов.
        """
        if status not in _SEVERITY:
            raise ValueError(f"Unknown status: {status!r}. Expected ok/degraded/down.")

        actual_today = today or datetime.now(tz=UTC).date()
        actual_now = now or datetime.now(tz=UTC)

        # Сначала пытаемся прочитать существующую запись (для escalation-логики).
        existing = await self._session.get(SystemUptimeDayORM, actual_today)

        if existing is None:
            orm = SystemUptimeDayORM(
                day=actual_today,
                status=status,
                first_seen_at=actual_now,
                last_seen_at=actual_now,
                worst_event_at=actual_now if status != "ok" else None,
                note=note,
            )
            self._session.add(orm)
            await self._session.flush()
            return orm

        # Эскалация worst-of-day.
        if _SEVERITY[status] > _SEVERITY[existing.status]:
            existing.status = status
            existing.worst_event_at = actual_now
            if note is not None:
                existing.note = note
        existing.last_seen_at = actual_now
        await self._session.flush()
        return existing

    async def list_last_n_days(
        self,
        *,
        n: int,
        today: date_type | None = None,
    ) -> list[SystemUptimeDayORM]:
        """Возвращает rows за последние ``n`` дней (включая today), отсортированные
        по day ASC. Пропуски не достраиваются — это делает frontend (grey-day).
        """
        if n <= 0:
            return []
        actual_today = today or datetime.now(tz=UTC).date()
        earliest = actual_today - timedelta(days=n - 1)

        stmt = (
            select(SystemUptimeDayORM)
            .where(SystemUptimeDayORM.day >= earliest)
            .where(SystemUptimeDayORM.day <= actual_today)
            .order_by(SystemUptimeDayORM.day.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def first_seen_day(self) -> date_type | None:
        """День самой первой записи — момент production-deploy системы.
        Используется UI для текста «Работаем с N мая 2026»."""
        stmt = (
            select(SystemUptimeDayORM.day)
            .order_by(SystemUptimeDayORM.day.asc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


# Sentinel: signal для not-yet-implemented integrations (faktura.uz и т.п.) —
# рендерится в UI как «В разработке», не как «С задержкой».
NOT_IMPLEMENTED_STATUS = "not_implemented"
