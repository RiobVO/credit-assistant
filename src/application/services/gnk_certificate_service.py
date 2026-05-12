"""GnkCertificateService — manual upload (T0.3 Phase A) + заглушка Phase B.

Phase A flow:
1. ``upload_for_borrower(...)`` — аналитик грузит PDF/JPG + указывает
   ручные поля (full_name, status, okveds, optional cert_id). Сохраняем
   binary в БД, возвращаем GnkCertificate с заполненным ``file_id``.

Phase B (CA-DS28, после legal review):
2. ``fetch_for_borrower(inn)`` — public lookup на soliq.uz/services/search/.
   Сейчас raise NotImplementedError — scaffolding для будущей integration
   через CBU-like fallback chain (mirror ADR-0014 pattern).

Mode-gating не у service — у router (`Depends(get_current_analyst)` в
``interfaces/api/shared/gnk_certificate.py``). Service сам по себе чистый.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from domain.value_objects.gnk_certificate import (
    GnkCertificate,
    GnkStatus,
)
from domain.value_objects.inn import INN
from infrastructure.persistence.repositories.gnk_certificate_repository import (
    SqlAlchemyGnkCertificateRepository,
)


class GnkCertificateService:
    def __init__(self, repository: SqlAlchemyGnkCertificateRepository) -> None:
        self._repo = repository

    async def upload_for_borrower(
        self,
        *,
        borrower_inn: INN,
        full_name: str,
        status: GnkStatus,
        okveds: list[str],
        cert_id: str | None,
        file_bytes: bytes,
        mime_type: str,
        analyst_id: UUID,
    ) -> GnkCertificate:
        """Phase A — manual upload. Сохраняет binary + parsed fields atomically."""
        now = datetime.now(tz=UTC)
        cert = GnkCertificate(
            borrower_inn=borrower_inn,
            full_name=full_name.strip(),
            status=status,
            okveds=_dedup_preserve_order(okveds),
            source="uploaded",
            cert_id=cert_id.strip() if cert_id else None,
            uploaded_at=now,
            uploaded_by_analyst_id=analyst_id,
        )
        return await self._repo.save(
            cert,
            file_bytes=file_bytes,
            mime_type=mime_type,
            uploaded_at=now,
        )

    async def get_latest_for_borrower(self, borrower_inn: INN) -> GnkCertificate | None:
        return await self._repo.get_latest_for_inn(borrower_inn)

    async def fetch_for_borrower(self, borrower_inn: INN) -> GnkCertificate:
        """Phase B (CA-DS28) — automatic lookup из soliq. Scaffolding."""
        raise NotImplementedError(
            f"Phase B (automatic ГНК lookup для {borrower_inn.value}) — "
            "ожидает legal-clearance CA-DS28; используй upload_for_borrower."
        )


def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        normalized = item.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out
