"""GET /api/system/health и /api/system/health/history — для UI Settings → О системе.

Health endpoint:
* Реальный ping Postgres (SELECT 1) → определяет статус «Поиск», «База клиентов»,
  «Импорт отчётности из Soliq» (все они зависят от БД).
* Lazy-import WeasyPrint → определяет статус «Генерация PDF-досье».
* faktura.uz интеграция ещё не реализована → статус ``not_implemented`` всегда
  (TODO[CA-DS11]); UI рендерит как «В разработке».
* UPSERT today's row в ``system_uptime_day`` для UI uptime-calendar.

History endpoint: возвращает рядом за последние ``days`` дней (default 30).
Frontend сам решает что показывать для пропусков (grey-day «до запуска»).

Auth: открыт без get_current_analyst — endpoint нужен для liveness-проб
и Settings-экрана как pre-auth (когда session expired, UI всё ещё хочет
показать «системы работают»). Никаких PII не утекает.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.catalog.exchange_rates import default_usd_uzs_rate
from infrastructure.catalog.okved_catalog import default_catalog as default_okved_catalog
from infrastructure.persistence.database import get_session
from infrastructure.persistence.repositories.system_uptime_repository import (
    NOT_IMPLEMENTED_STATUS,
    SqlAlchemySystemUptimeRepository,
)
from interfaces.api.shared.system_schema import (
    OkvedCatalogResponse,
    OkvedItem,
    ServiceStatus,
    SystemHealthResponse,
    UptimeDayItem,
    UptimeHistoryResponse,
    UsdRateResponse,
)

router = APIRouter(prefix="/api/system", tags=["system"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _check_weasyprint() -> bool:
    """Проверяет, что WeasyPrint доступен в текущем рантайме.

    В Docker-сервисе ``api`` (см. ADR-0008) Pango/HarfBuzz установлены и import
    проходит. На host-Windows без GTK import ломается — это ОК для dev, в
    production PDF-генерация в любом случае идёт из контейнера.
    """
    try:
        import weasyprint  # noqa: F401

        return True
    except Exception:
        return False


_OVERALL_PRIORITY = {"ok": 0, "degraded": 1, "down": 2}


def _worst(*statuses: str) -> str:
    """Возвращает худший среди не-not_implemented статусов. Если все
    not_implemented (теоретически невозможно) — возвращает 'ok'."""
    real = [s for s in statuses if s != NOT_IMPLEMENTED_STATUS]
    if not real:
        return "ok"
    return max(real, key=lambda s: _OVERALL_PRIORITY.get(s, 0))


@router.get("/health", response_model=SystemHealthResponse)
async def system_health(session: SessionDep) -> SystemHealthResponse:
    # 1. Postgres ping. Если БД недоступна — search/history/import-из-Soliq не работают.
    try:
        await session.execute(text("SELECT 1"))
        postgres_status = "ok"
    except Exception:
        postgres_status = "down"

    # 2. PDF-движок. WeasyPrint импорт-чек: на host-Windows может фейлиться.
    pdf_status = "ok" if _check_weasyprint() else "degraded"

    # 3. Конкретные сервисы — plain-language имена, маппинг к infra-проверкам.
    # Ключи стабильны (UI берёт их для i18n + иконки).
    services = [
        ServiceStatus(key="search", status=postgres_status),
        ServiceStatus(key="dossiers_db", status=postgres_status),
        ServiceStatus(key="soliq_import", status=postgres_status),
        ServiceStatus(
            key="pdf_generation",
            status=pdf_status,
            tip=(
                None
                if pdf_status == "ok"
                else "PDF-движок не запущен на этом узле. "
                "Скачивание досье будет с задержкой."
            ),
        ),
        ServiceStatus(
            key="faktura_uz",
            status=NOT_IMPLEMENTED_STATUS,
            tip=(
                "Подгрузка ЭСФ из faktura.uz пока в разработке. "
                "Можно вручную попросить выгрузку у клиента и подгрузить через Шаг 2 мастера."
            ),
        ),
    ]

    overall = _worst(*(svc.status for svc in services))

    # 4. UPSERT today в system_uptime_day. Худший статус дня сохраняется.
    repo = SqlAlchemySystemUptimeRepository(session)
    now = datetime.now(tz=UTC)
    # Если Postgres недоступен, мы сюда даже не дойдём (session.execute упал бы),
    # но если postgres_status='ok' а pdf='degraded' — пишем degraded на today.
    # UPSERT не должен ронять health-чек: даже если запись упала, сам status
    # уже посчитан и возвращается клиенту.
    with contextlib.suppress(Exception):
        await repo.upsert_today(status=overall, now=now)

    return SystemHealthResponse(
        status=overall,
        checked_at=now,
        services=services,
    )


@router.get("/health/history", response_model=UptimeHistoryResponse)
async def system_health_history(
    session: SessionDep,
    days: int = Query(default=30, ge=1, le=180),
) -> UptimeHistoryResponse:
    repo = SqlAlchemySystemUptimeRepository(session)
    rows = await repo.list_last_n_days(n=days)
    first_day = await repo.first_seen_day()
    return UptimeHistoryResponse(
        first_seen_day=first_day,
        days=[UptimeDayItem(day=row.day, status=row.status) for row in rows],
    )


@router.get("/usd-rate", response_model=UsdRateResponse)
async def system_usd_rate() -> UsdRateResponse:
    """USD/UZS rate для loan-wizard UI-конвертации (CA-DS24).

    Source priority: env ``USD_UZS_RATE`` > ``config/exchange/rates.json``.
    CBU API integration → CA-DS24b (legal review pre-condition).

    Singleton-cache (mirror OKVED endpoint): JSON парсится один раз;
    env-override фиксируется при первом вызове. Для re-evaluation —
    restart api контейнера.

    Auth: открыт без get_current_analyst — reference data, никаких PII.
    Decimal сериализуется строкой — сохраняем точность через JSON.
    """
    rate = default_usd_uzs_rate()
    return UsdRateResponse(
        rate=str(rate.rate),
        asof=rate.asof,
        source=rate.source,
    )


@router.get("/okved", response_model=OkvedCatalogResponse)
async def system_okved_catalog() -> OkvedCatalogResponse:
    """OKVED catalog МСБ-сегмента (CA-DS17).

    Источник — ``config/okved/uz_msb.json`` (single source для backend и
    frontend). Singleton-cache: JSON парсится один раз при первом обращении,
    при необходимости обновления — restart api контейнера.

    Auth: открыт без get_current_analyst — reference data, никаких PII.
    Frontend читает на mount manual-input wizard (Шаг 1 OkvedAutocomplete).
    """
    catalog = default_okved_catalog()
    items = sorted(catalog.list(), key=lambda e: e.code)
    return OkvedCatalogResponse(
        items=[
            OkvedItem(
                code=e.code,
                short_ru=e.short_ru,
                full_ru=e.full_ru,
                short_uz=e.short_uz,
                full_uz=e.full_uz,
            )
            for e in items
        ]
    )
