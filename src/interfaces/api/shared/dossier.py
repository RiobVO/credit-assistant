"""POST /api/manual-input — досье на основе ручного ввода.

Тонкий interfaces-слой: парсит payload, конвертирует в domain, прогоняет use
case + rules + scoring, возвращает structured response. Storage пока нет
(2.5 — Alembic + Postgres). Authentication пока нет (2.x — SSO/JWT).
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from application.use_cases.build_borrower_snapshot import build_borrower_snapshot
from domain.rules.rule import RuleRegistry
from domain.services.scoring_service import ScoringService
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service
from interfaces.api.shared.dossier_mapper import (
    build_dossier_response,
    to_borrower,
    to_manual_chunk,
)
from interfaces.api.shared.dossier_schema import DossierResponse, ManualInputRequest

router = APIRouter(prefix="/api", tags=["dossier"])

RuleRegistryDep = Annotated[RuleRegistry, Depends(get_rule_registry)]
ScoringServiceDep = Annotated[ScoringService, Depends(get_scoring_service)]


@router.post("/manual-input", response_model=DossierResponse)
def manual_input_dossier(
    payload: ManualInputRequest,
    registry: RuleRegistryDep,
    scoring: ScoringServiceDep,
) -> DossierResponse:
    borrower = to_borrower(payload.borrower)
    manual_chunk = to_manual_chunk(payload, borrower.inn)

    snapshot = build_borrower_snapshot(
        borrower=borrower,
        as_of=payload.as_of,
        chunks=[manual_chunk],
        loan_request=manual_chunk.loan_request,
    )

    flags = registry.run_all(snapshot)
    score = scoring.score(flags)

    return build_dossier_response(
        borrower_inn=borrower.inn,
        as_of=payload.as_of,
        flags=flags,
        score=score,
        rules_evaluated=len(registry.rules),
    )
