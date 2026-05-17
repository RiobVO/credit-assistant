"""GET /api/dossier/{id}/pdf — рендер досье в PDF.

Использует тот же ``LoadDossierForView`` use case, что и read endpoint
``GET /api/dossier/{id}``, плюс ``WeasyPrintPdfRenderer`` за
``PdfReportPort``-портом.

WeasyPrint требует Pango/HarfBuzz (см. ADR 0008). На Windows-хосте без GTK
endpoint вернёт 503 при первом обращении, в Docker (compose-сервис ``api``)
работает штатно.
"""

from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from application.use_cases.load_dossier_for_view import LoadDossierForView
from application.use_cases.render_dossier_pdf import RenderDossierPdf
from infrastructure.brand.brand_config import load_brand
from infrastructure.i18n.pdf_messages import default_pdf_messages
from infrastructure.persistence.repositories.audit_log_repository import (
    SqlAlchemyAuditLogRepository,
)
from infrastructure.reports.pdf.pdf_renderer import WeasyPrintPdfRenderer
from interfaces.api.bank.dependencies import OptionalAnalyst
from interfaces.api.shared.dependencies import get_rule_registry
from interfaces.api.shared.dossier_storage import SessionDep, StorageDep

router = APIRouter(prefix="/api", tags=["dossier"])


@lru_cache(maxsize=1)
def _get_pdf_renderer() -> WeasyPrintPdfRenderer:
    """Singleton: Jinja2 Environment + filter registry создаются один раз."""
    return WeasyPrintPdfRenderer()


@router.get(
    "/dossier/{dossier_id}/pdf",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF-досье. Content-Disposition: attachment.",
        },
        404: {"description": "Досье не найдено"},
        503: {"description": "PDF-рендер недоступен (нет GTK runtime)"},
    },
)
async def download_dossier_pdf(
    dossier_id: UUID,
    storage: StorageDep,
    session: SessionDep,
    analyst: OptionalAnalyst,
) -> Response:
    use_case = RenderDossierPdf(
        loader=LoadDossierForView(storage.dossier),
        renderer=_get_pdf_renderer(),
        rule_registry=get_rule_registry(),
        brand_loader=load_brand,
        # T0.4 / ADR-0015: default_pdf_messages — singleton с lru_cache(maxsize=2)
        # на ru+uz. ``?lang=`` query param добавляется в commit 8.
        pdf_messages_loader=default_pdf_messages,
    )

    try:
        pdf_bytes = await use_case.execute(dossier_id)
    except OSError as exc:
        # WeasyPrint падает с OSError при отсутствии libpango/libgobject —
        # отдаём осмысленный 503 вместо 500.
        raise HTTPException(
            status_code=503,
            detail=(
                "PDF-рендер недоступен в текущем окружении: "
                "WeasyPrint требует GTK runtime (Pango/HarfBuzz). "
                "Запустите backend в Docker compose-сервисе `api`."
            ),
        ) from exc

    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail="Досье не найдено")

    if analyst is not None:
        await SqlAlchemyAuditLogRepository(session).record(
            event="download_pdf",
            analyst_id=analyst.id,
            target_type="dossier",
            target_id=dossier_id,
        )

    filename = _build_filename(dossier_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


def _build_filename(dossier_id: UUID) -> str:
    """``BR-XXXX.pdf`` где XXXX — первые 4 hex uuid в верхнем регистре."""
    suffix = dossier_id.hex[:4].upper()
    return f"BR-{suffix}.pdf"
