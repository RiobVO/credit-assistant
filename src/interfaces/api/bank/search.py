"""GET /api/bank/borrowers/search — lookup заёмщика по ИНН.

Возвращает три варианта (см. design spec секция 4 и search_schema). Когда у
заёмщика есть bank-mode досье, дополнительно тянем ``DossierViewBundle`` и
заполняем ``card`` — даёт UI сразу: sparkline 12 мес, recommendation,
revenue_ltm + KPI, business_age, signals_total/evaluated. Без round-trip на
``/api/dossier/{id}``.

Записывает ``search_borrower`` в audit_log с masked-ИНН и result-status.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.bank_dossier_summary import BorrowerSearchHit
from application.use_cases.load_dossier_for_view import (
    DossierViewBundle,
    LoadDossierForView,
)
from config.settings import get_settings
from domain.value_objects.inn import INN, InvalidInnError
from infrastructure.persistence.database import get_session
from infrastructure.persistence.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
from infrastructure.persistence.repositories.dossier_repository import (
    SqlAlchemyDossierRepository,
)
from interfaces.api.bank.dependencies import CurrentAnalyst
from interfaces.api.bank.search_schema import (
    BorrowerSearchResponse,
    SearchCardData,
    SearchCardMonthlyPoint,
)

router = APIRouter(prefix="/api/bank/borrowers", tags=["bank-search"])


def _display_score(raw: int) -> int:
    """Phase 3.B convention: display_score = 100 - score, clamped 0..100."""
    return max(0, min(100, 100 - raw))


def _result_status(hit: BorrowerSearchHit) -> str:
    if not hit.found:
        return "not_found"
    if hit.dossier_id is None:
        return "borrower_only"
    return "with_dossier"


def _months_since(registration: date, today: date) -> int:
    """Целое число полных месяцев между двумя датами. Для отображения «возраст
    бизнеса» в UI. Дата регистрации может быть в будущем (тестовые данные) —
    возвращаем 0, не отрицательное.
    """
    months = (today.year - registration.year) * 12 + (today.month - registration.month)
    if today.day < registration.day:
        months -= 1
    return max(0, months)


def _build_card(bundle: DossierViewBundle, today: date) -> SearchCardData:
    snapshot = bundle.view.snapshot
    dossier = bundle.view.dossier

    revenue_ltm_kpi = bundle.kpis.revenue_ltm
    revenue_ltm: str | None = None
    yoy_pct: float | None = None
    if revenue_ltm_kpi is not None:
        revenue_ltm = str(revenue_ltm_kpi.value)
        if revenue_ltm_kpi.yoy_pct is not None:
            yoy_pct = float(revenue_ltm_kpi.yoy_pct)

    # Последние 12 точек из 24-месячного chart-данных.
    last_12 = bundle.monthly_revenue_24m[-12:]
    monthly_revenue_12m = [
        SearchCardMonthlyPoint(
            month=p.month_start.strftime("%Y-%m"),
            revenue=str(p.revenue.quantize(Decimal("1"))),
        )
        for p in last_12
    ]

    # `recommendation` в БД — уже строка "approve"/"review"/"reject" из
    # ScoringService.score(). Schema-уровень валидирует Literal.
    return SearchCardData(
        legal_form=snapshot.borrower.legal_form.value,
        recommendation=dossier.recommendation,
        revenue_ltm=revenue_ltm,
        yoy_pct=yoy_pct,
        business_age_months=_months_since(snapshot.borrower.registration_date, today),
        signals_total=len(dossier.red_flags),
        signals_evaluated=dossier.rules_evaluated,
        monthly_revenue_12m=monthly_revenue_12m,
    )


@router.get("/search", response_model=BorrowerSearchResponse)
async def search_borrower(
    analyst: CurrentAnalyst,
    session: Annotated[AsyncSession, Depends(get_session)],
    inn: Annotated[str, Query(min_length=9, max_length=14)],
) -> BorrowerSearchResponse:
    try:
        validated = INN(inn)
    except InvalidInnError as exc:
        # 422 = unprocessable. Имя константы starlette переименовали в
        # UNPROCESSABLE_CONTENT в 0.41; запись числом избегает deprecation.
        raise HTTPException(status_code=422, detail=f"invalid_inn: {exc}") from exc

    dossier_repo = SqlAlchemyDossierRepository(session)
    audit_log = SqlAlchemyAuditLogRepository(session, brand_id=get_settings().brand_id)

    hit = await dossier_repo.find_search_hit_by_inn(validated.value)

    await audit_log.record(
        event="search_borrower",
        analyst_id=analyst.id,
        target_type="borrower",
        target_id=hit.borrower_id,
        payload={"masked_inn": validated.masked, "result": _result_status(hit)},
    )

    card: SearchCardData | None = None
    if hit.dossier_id is not None:
        bundle = await LoadDossierForView(dossier_repo).execute(hit.dossier_id)
        if bundle is not None:
            card = _build_card(bundle, today=date.today())

    return BorrowerSearchResponse(
        found=hit.found,
        borrower_name=hit.borrower_name,
        dossier_id=hit.dossier_id,
        score=hit.score,
        display_score=_display_score(hit.score) if hit.score is not None else None,
        created_at=hit.created_at,
        card=card,
    )
