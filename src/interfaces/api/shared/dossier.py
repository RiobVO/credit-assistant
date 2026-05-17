"""POST /api/manual-input — досье на основе ручного ввода.

Тонкий interfaces-слой: парсит payload, конвертирует в domain, прогоняет use
case + rules + scoring, persistит результат и возвращает structured response.

GET /api/dossier/{dossier_id} (Phase 3.B) — read-модель экрана досье:
borrower + KPIs + 24-мес чарт + red flags. 404 если запись не найдена.

Phase 4.D: оба endpoint'а принимают optional analyst. На bank install
mode-gating в `app.py` навешивает строгий guard через router-level
``dependencies=[Depends(get_current_analyst)]`` → unauth получит 401 до
handler'а. Внутри handler оптонал используется для audit + проставления
``source_mode``/``created_by_analyst_id`` на новых досье.
"""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from application.dto.dossier_record import DossierRecord
from application.use_cases.build_borrower_snapshot import build_borrower_snapshot
from application.use_cases.load_dossier_for_view import LoadDossierForView
from application.use_cases.load_dossier_readiness import LoadDossierReadiness
from domain.rules.rule import RuleRegistry
from domain.services.scoring_service import ScoringService
from infrastructure.persistence.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
from interfaces.api.bank.dependencies import OptionalAnalyst
from interfaces.api.shared.data_readiness import _format_decimal
from interfaces.api.shared.data_readiness_schema import DataReadinessResponse
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
from interfaces.api.shared.dossier_storage import SessionDep, StorageDep

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
    session: SessionDep,
    analyst: OptionalAnalyst,
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
    # T1.1: case_id выдаёт CaseIdAllocator под текущий год; advisory lock
    # + sequence гарантируют monotonic в одной транзакции с save dossier.
    case_id = await storage.case_id_allocator.allocate(datetime.now(UTC))

    source_mode = "bank" if analyst is not None else "accountant"
    dossier_id = await storage.dossier.save(
        record,
        snapshot_id,
        case_id,
        source_mode=source_mode,
        created_by_analyst_id=analyst.id if analyst is not None else None,
    )

    if analyst is not None:
        await SqlAlchemyAuditLogRepository(session).record(
            event="generate_dossier",
            analyst_id=analyst.id,
            target_type="dossier",
            target_id=dossier_id,
            payload={"masked_inn": borrower.inn.masked, "source": "manual_input"},
        )

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
    session: SessionDep,
    analyst: OptionalAnalyst,
) -> DossierViewResponse:
    use_case = LoadDossierForView(storage.dossier)
    bundle = await use_case.execute(dossier_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Досье не найдено")

    if analyst is not None:
        await SqlAlchemyAuditLogRepository(session).record(
            event="view_dossier",
            analyst_id=analyst.id,
            target_type="dossier",
            target_id=dossier_id,
            payload={"masked_inn": bundle.view.snapshot.borrower.inn.masked},
        )

    return build_dossier_view_response(bundle)


@router.get("/dossier/{dossier_id}/readiness", response_model=DataReadinessResponse)
async def get_dossier_readiness(
    dossier_id: UUID,
    storage: StorageDep,
) -> DataReadinessResponse:
    """CA-035b: оценка готовности данных для готового досье.

    Зеркало POST /api/manual-input/readiness, но работает на persisted
    snapshot'е. `source_trail` в БД не хранится — восстанавливаем
    `set[ParserSource]` через heuristic по присутствию полей (см.
    `infer_parser_sources_from_snapshot`).

    Read-only, без audit-логирования: это derived view над уже доступным
    досье, не отдельное действие.
    """
    use_case = LoadDossierReadiness(storage.dossier)
    report = await use_case.execute(dossier_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Досье не найдено")
    return DataReadinessResponse(
        level=report.level.value,
        years_covered=list(report.years_covered),
        full_years=list(report.full_years),
        missing_capabilities=list(report.missing_capabilities),
        parser_sources=sorted(s.value for s in report.parser_sources),
        confidence_score=_format_decimal(report.confidence_score),
    )
