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

import csv
import io
import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse

from application.dto.analyst_identity import AnalystIdentity
from infrastructure.auth.email_mask import mask_email
from interfaces.api.bank.admin_audit_export_schema import AuditExportQuery
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
    # CA-DS16: stored bool удалён — enrolled_at NULL = mfa disabled.

    await audit_log.record(
        event="mfa_admin_reset",
        analyst_id=senior.id,
        payload={
            # T1.3 (ADR-0017): mask PII в audit payload.
            "target_email": mask_email(orm.email),
            "target_analyst_id": str(orm.id),
        },
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


_CSV_HEADER = [
    "id",
    "created_at",
    "brand_id",
    "request_id",
    "event",
    "analyst_id",
    "target_type",
    "target_id",
    "payload",
]


@router.get(
    "/audit-log/export",
    responses={
        403: {"description": "forbidden"},
        422: {"description": "invalid_query"},
    },
)
async def export_audit_log(
    query: Annotated[AuditExportQuery, Query()],
    audit_log: AuditLogRepoDep,
    senior: SeniorAnalystDep,
) -> StreamingResponse:
    """T3.5: CSV export audit-лога для compliance officer.

    Pull-model: handler читает все matching rows из БД (см. repo.export_range)
    и стримит CSV-байты клиенту. Сам факт экспорта пишется в audit_log
    отдельной записью ``audit_log_export`` — auditor видит, кто и какой
    срез данных вытащил.
    """
    rows = await audit_log.export_range(
        from_=query.from_, to=query.to, event=query.event
    )

    # Логируем сам экспорт ДО streaming'а, чтобы запись попала в БД даже
    # если клиент оборвёт connection mid-stream.
    await audit_log.record(
        event="audit_log_export",
        analyst_id=senior.id,
        payload={
            "from": query.from_.isoformat(),
            "to": query.to.isoformat(),
            "event_filter": query.event,
            "rows_count": len(rows),
        },
    )

    async def _generate() -> AsyncIterator[bytes]:
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writerow(_CSV_HEADER)
        yield buf.getvalue().encode("utf-8")
        buf.seek(0)
        buf.truncate()

        for row in rows:
            writer.writerow(
                [
                    str(row.id),
                    row.created_at.isoformat() if row.created_at else "",
                    row.brand_id,
                    row.request_id or "",
                    row.event,
                    str(row.analyst_id) if row.analyst_id else "",
                    row.target_type or "",
                    str(row.target_id) if row.target_id else "",
                    json.dumps(row.payload, ensure_ascii=False, sort_keys=True),
                ]
            )
            yield buf.getvalue().encode("utf-8")
            buf.seek(0)
            buf.truncate()

    filename = (
        f"audit-log-{query.from_.strftime('%Y%m%d')}"
        f"-{query.to.strftime('%Y%m%d')}.csv"
    )
    return StreamingResponse(
        _generate(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
