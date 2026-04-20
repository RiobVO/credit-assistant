"""POST /api/manual-input — досье на основе ручного ввода.

Тонкий interfaces-слой: парсит payload, конвертирует в domain, прогоняет use
case + rules + scoring, persistит результат и возвращает structured response.
Authentication пока нет (2.x — SSO/JWT).

GET /api/dossier/{dossier_id} (Phase 3.B) — read-модель экрана досье:
borrower + KPIs + 24-мес чарт + red flags. 404 если запись не найдена.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from application.dto.dossier_record import DossierRecord
from application.use_cases.build_borrower_snapshot import build_borrower_snapshot
from application.use_cases.load_dossier_for_view import LoadDossierForView
from domain.rules.rule import RuleRegistry
from domain.services.scoring_service import ScoringService
from interfaces.api.shared.dependencies import get_rule_registry, get_scoring_service
from interfaces.api.shared.dossier_mapper import (
    build_dossier_response,
    build_dossier_view_response,
    to_borrower,
    to_manual_chunk,
)
from interfaces.api.shared.dossier_schema import (
    DossierResponse,
    DossierViewResponse,
    ManualInputRequest,
)
from interfaces.api.shared.dossier_storage import StorageDep

router = APIRouter(prefix="/api", tags=["dossier"])

RuleRegistryDep = Annotated[RuleRegistry, Depends(get_rule_registry)]
ScoringServiceDep = Annotated[ScoringService, Depends(get_scoring_service)]

# Versioning rules engine: пока единственный YAML-файл = v1. Запишем как
# константу — при следующей итерации правил будет сравнение.
RULES_VERSION = "v1"


@router.post("/manual-input", response_model=DossierResponse)
async def manual_input_dossier(
    payload: ManualInputRequest,
    registry: RuleRegistryDep,
    scoring: ScoringServiceDep,
    storage: StorageDep,
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

    # Persist цепочкой: borrower → snapshot → dossier. Транзакция управляется
    # `get_session` зависимостью (commit на штатном выходе, rollback при exc).
    borrower_id = await storage.borrower.upsert(borrower)
    snapshot_id = await storage.snapshot.save(snapshot, borrower_id)
    record = DossierRecord(
        score=score.score,
        recommendation=score.recommendation.value,
        severity_breakdown={sev.value: cnt for sev, cnt in score.severity_breakdown.items()},
        red_flags=tuple(flags),
        rules_version=RULES_VERSION,
        rules_evaluated=len(registry.rules),
    )
    dossier_id = await storage.dossier.save(record, snapshot_id)

    return build_dossier_response(
        dossier_id=dossier_id,
        borrower_inn=borrower.inn,
        as_of=payload.as_of,
        flags=flags,
        score=score,
        rules_evaluated=len(registry.rules),
    )


@router.get("/dossier/{dossier_id}", response_model=DossierViewResponse)
async def get_dossier(
    dossier_id: UUID,
    storage: StorageDep,
) -> DossierViewResponse:
    use_case = LoadDossierForView(storage.dossier)
    bundle = await use_case.execute(dossier_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Досье не найдено")
    return build_dossier_view_response(bundle)
