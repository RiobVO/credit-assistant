"""LoadDossierForView: загрузка read-модели досье + KPI поверх неё.

Use case для GET /api/dossier/{id}. Тонкий orchestrator:
1) тянет ``DossierViewRecord`` через порт (один SELECT с двумя JOIN);
2) считает ``KpiBundle`` из ``snapshot``;
3) возвращает оба объекта одной записью ``DossierViewWithKpis``.

KPI-расчёт инкапсулирован тут, чтобы interfaces-слой (FastAPI endpoint)
оставался тонким — только парсинг path-param и сериализация ответа.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from application.dto.dossier_view_record import DossierViewRecord
from application.dto.kpi_bundle import KpiBundle, MonthlyRevenuePoint
from application.ports.dossier_view_repository_port import DossierViewRepositoryPort
from application.services.kpi_calculator import (
    compute_kpis,
    compute_monthly_revenue_24m,
)


@dataclass(frozen=True, slots=True)
class DossierViewBundle:
    """Полный результат use case: данные из БД + посчитанные представления."""

    view: DossierViewRecord
    kpis: KpiBundle
    monthly_revenue_24m: tuple[MonthlyRevenuePoint, ...]


class LoadDossierForView:
    def __init__(self, repo: DossierViewRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, dossier_id: UUID) -> DossierViewBundle | None:
        view = await self._repo.get_view_by_id(dossier_id)
        if view is None:
            return None
        return DossierViewBundle(
            view=view,
            kpis=compute_kpis(view.snapshot),
            monthly_revenue_24m=compute_monthly_revenue_24m(view.snapshot),
        )
