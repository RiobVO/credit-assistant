"""GET /api/bank/borrowers/search — lookup заёмщика по ИНН.

Возвращает три варианта (см. design spec секция 4 и search_schema). Записывает
``search_borrower`` в audit_log с masked-ИНН и result-status.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.bank_dossier_summary import BorrowerSearchHit
from domain.value_objects.inn import INN, InvalidInnError
from infrastructure.persistence.database import get_session
from infrastructure.persistence.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
from infrastructure.persistence.repositories.dossier_repository import (
    SqlAlchemyDossierRepository,
)
from interfaces.api.bank.dependencies import CurrentAnalyst
from interfaces.api.bank.search_schema import BorrowerSearchResponse

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
    audit_log = SqlAlchemyAuditLogRepository(session)

    hit = await dossier_repo.find_search_hit_by_inn(validated.value)

    await audit_log.record(
        event="search_borrower",
        analyst_id=analyst.id,
        target_type="borrower",
        target_id=hit.borrower_id,
        payload={"masked_inn": validated.masked, "result": _result_status(hit)},
    )

    return BorrowerSearchResponse(
        found=hit.found,
        borrower_name=hit.borrower_name,
        dossier_id=hit.dossier_id,
        score=hit.score,
        display_score=_display_score(hit.score) if hit.score is not None else None,
        created_at=hit.created_at,
    )
