"""GET /api/bank/stats/today — live-strip метрики для /search hero.

Daily-агрегация bank-mode dossiers за UTC-сегодня:
* collected_today — всего собрано
* approved_pct — % с recommendation='approve' (None если today=0 — избегаем
  «0%» false-signal)
* in_review_today — recommendation='review'

Один SELECT с count(*) FILTER через ORM. Auth — JWT bank-analyst.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.persistence.database import get_session
from infrastructure.persistence.repositories.dossier_repository import (
    SqlAlchemyDossierRepository,
)
from interfaces.api.bank.dependencies import CurrentAnalyst

router = APIRouter(prefix="/api/bank/stats", tags=["bank-stats"])


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BankDailyStatsResponse(_StrictModel):
    collected_today: int
    approved_pct: int | None
    in_review_today: int


def _utc_today() -> date:
    """UTC «today» — единая точка получения даты, для inject в тестах."""
    return datetime.now(UTC).date()


@router.get("/today", response_model=BankDailyStatsResponse)
async def daily_stats(
    _analyst: CurrentAnalyst,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BankDailyStatsResponse:
    repo = SqlAlchemyDossierRepository(session)
    stats = await repo.get_bank_daily_stats(_utc_today())
    return BankDailyStatsResponse(
        collected_today=stats.collected_today,
        approved_pct=stats.approved_pct,
        in_review_today=stats.in_review_today,
    )
