"""ГНК-справки endpoint — manual upload Phase A (T0.3, CA-003).

Endpoints:
- ``POST /api/borrowers/{inn}/gnk-certificate`` — multipart upload PDF/JPG +
  ручные поля (full_name, status, okveds, optional cert_id).
- ``GET /api/borrowers/{inn}/gnk-certificate`` — latest для borrower (без bytes).
- ``GET /api/gnk-certificates/{cert_id}/file`` — download binary.

Mode-gating: bank-only с auth (см. ``app.py``). Accountant install не подключает
этот router (аналитик банка единственный кто грузит ГНК — это compliance audit).

Validation:
- file size ≤ 5MB (banking-typical for PDF справки)
- mime_type ∈ {application/pdf, image/jpeg, image/png}
- status ∈ {active, suspended, revoked, unknown}
"""

from __future__ import annotations

from typing import Annotated, get_args
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.analyst_identity import AnalystIdentity
from application.services.gnk_certificate_service import GnkCertificateService
from domain.value_objects.gnk_certificate import GnkStatus
from domain.value_objects.inn import INN, InvalidInnError
from infrastructure.persistence.database import get_session
from infrastructure.persistence.repositories.gnk_certificate_repository import (
    SqlAlchemyGnkCertificateRepository,
)
from interfaces.api.bank.dependencies import get_current_analyst

router = APIRouter(prefix="/api", tags=["gnk-certificate"])

_MAX_FILE_BYTES = 5 * 1024 * 1024
_ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
_ALLOWED_STATUSES = set(get_args(GnkStatus))


class GnkCertificateResponse(BaseModel):
    """Public представление ГНК-справки. file_bytes никогда не уходит — только
    через separate download endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    file_id: UUID | None = Field(default=None)
    borrower_inn: str
    full_name: str
    status: str
    okveds: list[str]
    source: str
    cert_id: str | None = None
    uploaded_at: str | None = None
    uploaded_by_analyst_id: UUID | None = None


_SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _get_service(session: _SessionDep) -> GnkCertificateService:
    return GnkCertificateService(SqlAlchemyGnkCertificateRepository(session))


_ServiceDep = Annotated[GnkCertificateService, Depends(_get_service)]
_AnalystDep = Annotated[AnalystIdentity, Depends(get_current_analyst)]


@router.post(
    "/borrowers/{inn}/gnk-certificate",
    response_model=GnkCertificateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_gnk_certificate(
    inn: str,
    service: _ServiceDep,
    analyst: _AnalystDep,
    file: Annotated[UploadFile, File(description="ГНК-справка (PDF/JPG/PNG, ≤5MB)")],
    full_name: Annotated[str, Form(min_length=1, max_length=500)],
    cert_status: Annotated[str, Form(description="active | suspended | revoked | unknown")],
    okveds: Annotated[str, Form(description="ОКВЭДы через запятую")] = "",
    cert_id: Annotated[str | None, Form()] = None,
) -> GnkCertificateResponse:
    parsed_inn = _parse_inn(inn)
    parsed_status = _parse_status(cert_status)
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=422, detail="file is empty")
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"file too large: {len(file_bytes)} bytes (max {_MAX_FILE_BYTES})",
        )
    mime = (file.content_type or "").lower()
    if mime not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported mime: {mime!r}; expected one of {sorted(_ALLOWED_MIME_TYPES)}",
        )

    okveds_list = [code.strip() for code in okveds.split(",") if code.strip()]
    saved = await service.upload_for_borrower(
        borrower_inn=parsed_inn,
        full_name=full_name,
        status=parsed_status,
        okveds=okveds_list,
        cert_id=cert_id,
        file_bytes=file_bytes,
        mime_type=mime,
        analyst_id=analyst.id,
    )
    return _to_response(saved)


@router.get(
    "/borrowers/{inn}/gnk-certificate",
    response_model=GnkCertificateResponse,
)
async def get_latest_gnk_certificate(
    inn: str,
    service: _ServiceDep,
) -> GnkCertificateResponse:
    parsed_inn = _parse_inn(inn)
    cert = await service.get_latest_for_borrower(parsed_inn)
    if cert is None:
        raise HTTPException(status_code=404, detail=f"no certificate for INN {parsed_inn.value}")
    return _to_response(cert)


@router.get("/gnk-certificates/{cert_id}/file")
async def download_gnk_certificate_file(
    cert_id: UUID,
    session: _SessionDep,
) -> Response:
    repo = SqlAlchemyGnkCertificateRepository(session)
    found = await repo.get_by_id(cert_id)
    if found is None:
        raise HTTPException(status_code=404, detail="certificate not found")
    _, file_bytes, mime = found
    if file_bytes is None:
        raise HTTPException(status_code=404, detail="certificate has no binary content")
    return Response(content=file_bytes, media_type=mime or "application/octet-stream")


def _parse_inn(raw: str) -> INN:
    try:
        return INN(raw)
    except InvalidInnError as exc:
        raise HTTPException(status_code=422, detail=f"invalid INN: {exc}") from exc


def _parse_status(raw: str) -> GnkStatus:
    if raw not in _ALLOWED_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"invalid status {raw!r}; expected one of {sorted(_ALLOWED_STATUSES)}",
        )
    return raw  # type: ignore[return-value]


def _to_response(cert: object) -> GnkCertificateResponse:
    # cert == GnkCertificate (frozen dataclass) — конверсия через attribute access.
    return GnkCertificateResponse(
        file_id=cert.file_id,  # type: ignore[attr-defined]
        borrower_inn=cert.borrower_inn.value,  # type: ignore[attr-defined]
        full_name=cert.full_name,  # type: ignore[attr-defined]
        status=cert.status,  # type: ignore[attr-defined]
        okveds=list(cert.okveds),  # type: ignore[attr-defined]
        source=cert.source,  # type: ignore[attr-defined]
        cert_id=cert.cert_id,  # type: ignore[attr-defined]
        uploaded_at=cert.uploaded_at.isoformat() if cert.uploaded_at else None,  # type: ignore[attr-defined]
        uploaded_by_analyst_id=cert.uploaded_by_analyst_id,  # type: ignore[attr-defined]
    )
