"""Integration test SqlAlchemyGnkCertificateRepository — testcontainers (T0.3)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.value_objects.gnk_certificate import GnkCertificate
from domain.value_objects.inn import INN
from infrastructure.persistence.models.analyst import AnalystORM
from infrastructure.persistence.repositories.gnk_certificate_repository import (
    SqlAlchemyGnkCertificateRepository,
)

pytestmark = pytest.mark.integration


async def _seed_analyst(session: AsyncSession) -> UUID:
    analyst = AnalystORM(
        email="test-analyst-gnk@example.com",
        full_name="Test Analyst",
        role="analyst",
        password_hash="x",
        is_active=True,
    )
    session.add(analyst)
    await session.flush()
    return analyst.id


async def test_save_returns_cert_with_file_id_and_persists_metadata(
    pg_session: AsyncSession,
) -> None:
    analyst_id = await _seed_analyst(pg_session)
    repo = SqlAlchemyGnkCertificateRepository(pg_session)
    cert = GnkCertificate(
        borrower_inn=INN("305002665"),
        full_name='"ZAMIN NOZ NEMATLARI" MCHJ',
        status="active",
        okveds=["47.11"],
        source="uploaded",
        cert_id="GNK-2026-1",
        uploaded_at=datetime.now(tz=UTC),
        uploaded_by_analyst_id=analyst_id,
    )
    saved = await repo.save(
        cert,
        file_bytes=b"%PDF-1.4 stub",
        mime_type="application/pdf",
        uploaded_at=cert.uploaded_at or datetime.now(tz=UTC),
    )
    assert saved.file_id is not None
    assert saved.borrower_inn.value == "305002665"
    assert saved.uploaded_by_analyst_id == analyst_id


async def test_get_latest_returns_most_recently_uploaded(
    pg_session: AsyncSession,
) -> None:
    analyst_id = await _seed_analyst(pg_session)
    repo = SqlAlchemyGnkCertificateRepository(pg_session)
    inn = INN("308747266")
    for i, status_value in enumerate(["suspended", "active"]):
        await repo.save(
            GnkCertificate(
                borrower_inn=inn,
                full_name="X",
                status=status_value,  # type: ignore[arg-type]
                uploaded_at=datetime(2026, 5, 17 + i, 12, 0, tzinfo=UTC),
                uploaded_by_analyst_id=analyst_id,
            ),
            file_bytes=b"x",
            mime_type="application/pdf",
            uploaded_at=datetime(2026, 5, 17 + i, 12, 0, tzinfo=UTC),
        )
    latest = await repo.get_latest_for_inn(inn)
    assert latest is not None
    assert latest.status == "active"  # последний по uploaded_at


async def test_get_by_id_returns_dto_with_file_bytes(pg_session: AsyncSession) -> None:
    analyst_id = await _seed_analyst(pg_session)
    repo = SqlAlchemyGnkCertificateRepository(pg_session)
    inn = INN("201308534")
    saved = await repo.save(
        GnkCertificate(
            borrower_inn=inn,
            full_name="X",
            status="active",
            uploaded_by_analyst_id=analyst_id,
        ),
        file_bytes=b"%PDF-1.4 binary",
        mime_type="application/pdf",
        uploaded_at=datetime.now(tz=UTC),
    )
    assert saved.file_id is not None
    got = await repo.get_by_id(saved.file_id)
    assert got is not None
    dto, file_bytes, mime = got
    assert dto.borrower_inn.value == "201308534"
    assert file_bytes == b"%PDF-1.4 binary"
    assert mime == "application/pdf"


async def test_get_latest_returns_none_when_no_certs(pg_session: AsyncSession) -> None:
    repo = SqlAlchemyGnkCertificateRepository(pg_session)
    assert await repo.get_latest_for_inn(INN("999999999")) is None
