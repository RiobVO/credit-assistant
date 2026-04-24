"""POST /api/manual-input/readiness — оценка готовности данных черновика.

Stateless: фронт шлёт аналитический срез form state Шага 2 + source_trail
(см. ``data_readiness_schema.py``), бэк строит синтетический ``BorrowerSnapshot``
и вызывает ``domain.assess_readiness``. Результат — 4-уровневая шкала +
missing_capabilities + confidence_score (см. ADR 0010).

Mode-gating: на bank install router закрыт ``Depends(get_current_analyst)``
(см. ``app.py``). На accountant install — открыт.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter

from application.use_cases.assess_draft_readiness import (
    AssessDraftReadinessInput,
    assess_draft_readiness,
)
from interfaces.api.shared.data_readiness_schema import (
    DataReadinessRequest,
    DataReadinessResponse,
)


def _format_decimal(d: Decimal) -> str:
    """Decimal → compact str без хвостовых нулей.

    Domain накапливает score через арифметику ``Decimal("0.25") * N``, что
    оставляет scale (``Decimal("0.00")``, ``Decimal("1.00")``). Для JSON API
    обрезаем хвостовые нули и точку: "0", "0.25", "1" (а не "0.00" / "1.00").
    """
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"

router = APIRouter(prefix="/api/manual-input", tags=["manual-input"])


@router.post("/readiness", response_model=DataReadinessResponse)
async def assess_readiness_endpoint(
    body: DataReadinessRequest,
) -> DataReadinessResponse:
    """Оценить готовность данных черновика к скоринговому прогону.

    Stateless: не читает БД, не сохраняет состояние. Frontend дебаунсит
    запросы (500ms) при изменениях step2 form.
    """
    report = assess_draft_readiness(
        AssessDraftReadinessInput(
            annual_report_years=body.annual_report_years,
            full_quarter_years=body.full_quarter_years,
            partial_quarter_years=body.partial_quarter_years,
            source_trail=body.source_trail,
        )
    )
    return DataReadinessResponse(
        level=report.level.value,
        years_covered=list(report.years_covered),
        full_years=list(report.full_years),
        missing_capabilities=list(report.missing_capabilities),
        parser_sources=sorted(s.value for s in report.parser_sources),
        confidence_score=_format_decimal(report.confidence_score),
    )
