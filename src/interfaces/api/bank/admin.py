"""POST /api/bank/admin/* — операции, доступные только senior_analyst.

В v1 единственный endpoint — `reset-mfa` (CA-DS13). Сценарий: аналитик
потерял телефон + backup-коды → senior очищает mfa_secret/enrolled_at/
backup_codes_hash. На следующий login пользователь зайдёт без 2FA-шага
и сможет re-enroll'нуться заново.

Force-logout не нужен: JWT в v1 stateless (TODO[CA-019]). Access TTL 15 мин
истечёт сам; на refresh пользователь не получит challenge (computed
mfa_enabled = False после reset), но и не залогаутится — это поведение
приемлемо для v1, поскольку reset инициирует senior_analyst после
звонка/тикета от затронутого user.

Audit: ``mfa_admin_reset`` с payload {target_email, target_analyst_id}.
analyst_id в записи — это **senior**, который инициировал; payload даёт
след до затронутого user.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from application.dto.analyst_identity import AnalystIdentity
from interfaces.api.bank.admin_schema import AdminResetMfaRequest
from interfaces.api.bank.dependencies import (
    AnalystRepoDep,
    AuditLogRepoDep,
    CurrentAnalyst,
)

router = APIRouter(prefix="/api/bank/admin", tags=["bank-admin"])


async def require_senior_analyst(analyst: CurrentAnalyst) -> AnalystIdentity:
    """Guard для admin-endpoints: только role=senior_analyst пропускается.

    Возвращает identity для дальнейшего использования в handler'е (audit).
    """
    if analyst.role != "senior_analyst":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return analyst


SeniorAnalystDep = Annotated[AnalystIdentity, Depends(require_senior_analyst)]


@router.post(
    "/analysts/reset-mfa",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"description": "forbidden"},
        404: {"description": "analyst_not_found"},
    },
)
async def reset_mfa(
    payload: AdminResetMfaRequest,
    analyst_repo: AnalystRepoDep,
    audit_log: AuditLogRepoDep,
    senior: SeniorAnalystDep,
) -> Response:
    orm = await analyst_repo.get_orm_by_email(payload.email)
    if orm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="analyst_not_found"
        )

    orm.mfa_secret = None
    orm.mfa_enrolled_at = None
    orm.mfa_backup_codes_hash = None
    orm.mfa_enabled = False

    await audit_log.record(
        event="mfa_admin_reset",
        analyst_id=senior.id,
        payload={"target_email": orm.email, "target_analyst_id": str(orm.id)},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
