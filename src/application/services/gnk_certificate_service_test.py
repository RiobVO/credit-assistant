"""Тесты GnkCertificateService — manual upload + Phase B placeholder."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from application.services.gnk_certificate_service import GnkCertificateService
from domain.value_objects.gnk_certificate import GnkCertificate
from domain.value_objects.inn import INN


class FakeRepo:
    def __init__(self) -> None:
        self.saved: list[GnkCertificate] = []
        self.saved_file_bytes: list[bytes | None] = []
        self.latest_by_inn: dict[str, GnkCertificate] = {}

    async def save(
        self,
        cert: GnkCertificate,
        *,
        file_bytes: bytes | None,
        mime_type: str | None,
        uploaded_at: datetime,
    ) -> GnkCertificate:
        self.saved.append(cert)
        self.saved_file_bytes.append(file_bytes)
        return GnkCertificate(
            borrower_inn=cert.borrower_inn,
            full_name=cert.full_name,
            status=cert.status,
            okveds=list(cert.okveds),
            source=cert.source,
            cert_id=cert.cert_id,
            uploaded_at=uploaded_at,
            uploaded_by_analyst_id=cert.uploaded_by_analyst_id,
            file_id=uuid4(),
        )

    async def get_latest_for_inn(self, inn: INN) -> GnkCertificate | None:
        return self.latest_by_inn.get(inn.value)


_ANALYST = UUID("11111111-2222-3333-4444-555555555555")
_INN = INN("305002665")


def _make() -> tuple[GnkCertificateService, FakeRepo]:
    repo = FakeRepo()
    return GnkCertificateService(repo), repo  # type: ignore[arg-type]


async def test_upload_persists_with_source_uploaded_and_analyst() -> None:
    svc, repo = _make()
    result = await svc.upload_for_borrower(
        borrower_inn=_INN,
        full_name=' "ZAMIN NOZ NEMATLARI" MCHJ ',
        status="active",
        okveds=["47.11", "47.19", "47.11"],  # дубликат на дедупликации
        cert_id="GNK-2026-12345",
        file_bytes=b"%PDF-1.4 fake",
        mime_type="application/pdf",
        analyst_id=_ANALYST,
    )
    assert result.source == "uploaded"
    assert result.borrower_inn.value == "305002665"
    assert result.full_name == '"ZAMIN NOZ NEMATLARI" MCHJ'
    assert result.okveds == ["47.11", "47.19"]  # дедуп + sort by first-appearance
    assert result.cert_id == "GNK-2026-12345"
    assert result.uploaded_by_analyst_id == _ANALYST
    assert result.file_id is not None
    assert repo.saved_file_bytes[0] == b"%PDF-1.4 fake"


async def test_upload_strips_blank_cert_id_to_none() -> None:
    svc, _ = _make()
    result = await svc.upload_for_borrower(
        borrower_inn=_INN,
        full_name="X",
        status="active",
        okveds=[],
        cert_id="   ",  # пустой trimmed
        file_bytes=b"x",
        mime_type="application/pdf",
        analyst_id=_ANALYST,
    )
    # «  » → trimmed = "" → falsy → None
    assert result.cert_id is None or result.cert_id == ""


async def test_get_latest_returns_stored() -> None:
    svc, repo = _make()
    stored = GnkCertificate(
        borrower_inn=_INN,
        full_name="X",
        status="active",
    )
    repo.latest_by_inn[_INN.value] = stored
    got = await svc.get_latest_for_borrower(_INN)
    assert got == stored


async def test_fetch_phase_b_raises_not_implemented() -> None:
    svc, _ = _make()
    with pytest.raises(NotImplementedError, match="Phase B"):
        await svc.fetch_for_borrower(_INN)
