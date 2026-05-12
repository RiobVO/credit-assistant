"""SqlAlchemyGnkCertificateRepository — manual upload + retrieve (T0.3 Phase A).

Read API:
- ``get_latest_for_inn(inn)`` → последняя загруженная справка для borrower.
- ``get_by_id(cert_id)`` → справка + file_bytes для download.
- ``get_metadata_by_id(cert_id)`` → справка без file_bytes (для list/preview).

Write API:
- ``save(cert, file_bytes, mime_type)`` → создаёт row с auto-generated UUID,
  возвращает обновлённый GnkCertificate с заполненным ``file_id``.

История: одна фирма может иметь N справок (re-upload при обновлении статуса).
``get_latest_for_inn`` берёт самую свежую по ``uploaded_at DESC``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.value_objects.gnk_certificate import (
    GnkCertificate,
    GnkSource,
    GnkStatus,
)
from domain.value_objects.inn import INN
from infrastructure.persistence.models.gnk_certificate import GnkCertificateORM


class SqlAlchemyGnkCertificateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_for_inn(self, inn: INN) -> GnkCertificate | None:
        stmt = (
            select(GnkCertificateORM)
            .where(GnkCertificateORM.borrower_inn == inn.value)
            .order_by(GnkCertificateORM.uploaded_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return _to_dto(orm) if orm is not None else None

    async def get_by_id(
        self, cert_id: UUID
    ) -> tuple[GnkCertificate, bytes | None, str | None] | None:
        """Полный read для download endpoint — возвращает справку + file_bytes + mime."""
        orm = await self._session.get(GnkCertificateORM, cert_id)
        if orm is None:
            return None
        return _to_dto(orm), orm.file_bytes, orm.mime_type

    async def save(
        self,
        cert: GnkCertificate,
        *,
        file_bytes: bytes | None,
        mime_type: str | None,
        uploaded_at: datetime,
    ) -> GnkCertificate:
        orm = GnkCertificateORM(
            borrower_inn=cert.borrower_inn.value,
            full_name=cert.full_name,
            status=cert.status,
            okveds=list(cert.okveds),
            cert_id=cert.cert_id,
            source=cert.source,
            file_bytes=file_bytes,
            mime_type=mime_type,
            file_size_bytes=len(file_bytes) if file_bytes is not None else None,
            uploaded_at=uploaded_at,
            uploaded_by_analyst_id=cert.uploaded_by_analyst_id,
        )
        self._session.add(orm)
        await self._session.flush()
        # orm.id заполнен server_default-ом после flush.
        return GnkCertificate(
            borrower_inn=cert.borrower_inn,
            full_name=cert.full_name,
            status=cert.status,
            okveds=list(cert.okveds),
            source=cert.source,
            cert_id=cert.cert_id,
            uploaded_at=uploaded_at,
            uploaded_by_analyst_id=cert.uploaded_by_analyst_id,
            file_id=orm.id,
        )


def _to_dto(orm: GnkCertificateORM) -> GnkCertificate:
    return GnkCertificate(
        borrower_inn=INN(orm.borrower_inn),
        full_name=orm.full_name,
        status=_status(orm.status),
        okveds=list(orm.okveds),
        source=_source(orm.source),
        cert_id=orm.cert_id,
        uploaded_at=orm.uploaded_at,
        uploaded_by_analyst_id=orm.uploaded_by_analyst_id,
        file_id=orm.id,
    )


def _status(raw: str) -> GnkStatus:
    if raw in ("active", "suspended", "revoked", "unknown"):
        return raw  # type: ignore[return-value]
    return "unknown"


def _source(raw: str) -> GnkSource:
    if raw in ("uploaded", "gnk_live", "gnk_cached", "fallback"):
        return raw  # type: ignore[return-value]
    return "uploaded"
