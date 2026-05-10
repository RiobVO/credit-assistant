"""GET /api/bank/dossiers — пагинированная история bank-mode досье.

Фильтр ``filter=mine`` сужает по ``created_by_analyst_id = current_analyst``.
``q`` — текстовый поиск по ИНН и имени заёмщика (ILIKE). Пагинация standard
offset/limit, max page_size=100.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from domain.value_objects.inn import INN
from infrastructure.persistence.database import get_session
from infrastructure.persistence.repositories.dossier_repository import (
    SqlAlchemyDossierRepository,
)
from interfaces.api.bank.dependencies import CurrentAnalyst
from interfaces.api.bank.search_schema import (
    BankDossierListItemResponse,
    BankDossierListResponse,
    ListFilter,
)

router = APIRouter(prefix="/api/bank/dossiers", tags=["bank-history"])


def _display_score(raw: int) -> int:
    return max(0, min(100, 100 - raw))


def _mask_inn(inn: str) -> str:
    # Та же логика, что INN.masked, но без необходимости валидировать строку
    # из БД через value object (она уже была валидной при upsert).
    if len(inn) <= 4:
        return inn
    return "X" * (len(inn) - 4) + inn[-4:]


# Если query "выглядит как ИНН" (только цифры, 9 или 14 знаков), нормализуем
# через INN — это убирает пробелы и даёт точное совпадение. Иначе оставляем
# подстроку для ILIKE по имени.
def _normalize_query(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    if cleaned.isdigit() and len(cleaned) in (9, 14):
        try:
            return INN(cleaned).value
        except Exception:
            return cleaned
    return cleaned


@router.get("", response_model=BankDossierListResponse)
async def list_dossiers(
    analyst: CurrentAnalyst,
    session: Annotated[AsyncSession, Depends(get_session)],
    filter: Annotated[ListFilter, Query()] = "all",
    q: Annotated[str | None, Query(max_length=255)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BankDossierListResponse:
    repo = SqlAlchemyDossierRepository(session)
    result = await repo.list_bank_dossiers(
        analyst_id=analyst.id,
        only_mine=filter == "mine",
        query=_normalize_query(q),
        page=page,
        page_size=page_size,
    )

    items = [
        BankDossierListItemResponse(
            dossier_id=item.dossier_id,
            borrower_inn_masked=_mask_inn(item.inn),
            borrower_name=item.borrower_name,
            score=item.score,
            display_score=_display_score(item.score),
            recommendation=item.recommendation,
            created_at=item.created_at,
            analyst_id=item.analyst_id,
            analyst_full_name=item.analyst_full_name,
        )
        for item in result.items
    ]
    return BankDossierListResponse(
        items=items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )
