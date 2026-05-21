"""Integration: PII columns шифруются в БД (raw SELECT даёт ciphertext)
и расшифровываются прозрачно через ORM (T1.3 / ADR-0017).

Не дублирует unit-тесты TypeDecorator'а — проверяет реальную интеграцию с
Postgres через testcontainers + AsyncSession + ORM.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from pytest import MonkeyPatch
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import encryption as encryption_module
from config.encryption import get_pii_encryptor
from infrastructure.encryption.fernet_pii_encryptor import FernetPiiEncryptor
from infrastructure.persistence.models.analyst import AnalystORM
from infrastructure.persistence.models.borrower import BorrowerORM
from infrastructure.persistence.models.borrower_snapshot import BorrowerSnapshotORM
from infrastructure.persistence.models.draft import DraftORM
from infrastructure.persistence.models.gnk_certificate import GnkCertificateORM

pytestmark = pytest.mark.integration


@pytest.fixture
def fernet_active(monkeypatch: MonkeyPatch) -> Iterator[FernetPiiEncryptor]:
    """Активирует Fernet encryptor на время теста — заменяет module-level
    `config.encryption.get_pii_encryptor`. TypeDecorator'ы импортируют
    module-attribute, поэтому patch видим всем колонкам."""
    key = Fernet.generate_key().decode("ascii")
    enc = FernetPiiEncryptor([key])
    get_pii_encryptor.cache_clear()
    monkeypatch.setattr(encryption_module, "get_pii_encryptor", lambda: enc)
    yield enc
    get_pii_encryptor.cache_clear()


async def test_analyst_full_name_encrypted_at_rest(
    pg_session: AsyncSession, fernet_active: FernetPiiEncryptor
) -> None:
    orm = AnalystORM(
        email="enc-test@bank.uz",
        password_hash="$2b$04$dummy",
        full_name="Иванов И.И.",
        role="analyst",
        is_active=True,
    )
    pg_session.add(orm)
    await pg_session.flush()
    analyst_id = orm.id

    raw = (
        await pg_session.execute(
            text("SELECT full_name FROM analysts WHERE id=:id"),
            {"id": analyst_id},
        )
    ).scalar_one()
    assert isinstance(raw, str)
    assert raw != "Иванов И.И."
    assert raw.startswith("gAAAAA")

    # ORM SELECT — transparent decrypt.
    fresh = (
        await pg_session.execute(
            text("SELECT full_name FROM analysts WHERE id=:id"),
            {"id": analyst_id},
        )
    ).scalar_one()
    # Через ORM — refresh даёт decrypted значение.
    pg_session.expire(orm)
    await pg_session.refresh(orm)
    assert orm.full_name == "Иванов И.И."
    assert raw == fresh  # raw остаётся ciphertext (контракт sanity-check)


async def test_analyst_mfa_secret_encrypted_at_rest(
    pg_session: AsyncSession, fernet_active: FernetPiiEncryptor
) -> None:
    orm = AnalystORM(
        email="mfa-enc@bank.uz",
        password_hash="$2b$04$dummy",
        full_name="MFA Test",
        role="analyst",
        is_active=True,
        mfa_secret="JBSWY3DPEHPK3PXP",
    )
    pg_session.add(orm)
    await pg_session.flush()

    raw = (
        await pg_session.execute(
            text("SELECT mfa_secret FROM analysts WHERE id=:id"),
            {"id": orm.id},
        )
    ).scalar_one()
    assert raw.startswith("gAAAAA")

    pg_session.expire(orm, ["mfa_secret"])
    await pg_session.refresh(orm)
    assert orm.mfa_secret == "JBSWY3DPEHPK3PXP"


async def test_borrower_director_name_encrypted_at_rest(
    pg_session: AsyncSession, fernet_active: FernetPiiEncryptor
) -> None:
    orm = BorrowerORM(
        inn=f"99{uuid4().hex[:7]}",
        name='OOO "Test"',
        legal_form="LLC",
        registration_date=date(2020, 1, 1),
        director_name="Петров П.П.",
        director_appointed_at=date(2021, 1, 1),
        oked_main="62.01",
        registered_address="Ташкент",
    )
    pg_session.add(orm)
    await pg_session.flush()

    raw = (
        await pg_session.execute(
            text("SELECT director_name FROM borrowers WHERE id=:id"),
            {"id": orm.id},
        )
    ).scalar_one()
    assert raw.startswith("gAAAAA")

    pg_session.expire(orm, ["director_name"])
    await pg_session.refresh(orm)
    assert orm.director_name == "Петров П.П."


async def test_borrower_snapshot_payload_wrapped_in_jsonb(
    pg_session: AsyncSession, fernet_active: FernetPiiEncryptor
) -> None:
    borrower = BorrowerORM(
        inn=f"99{uuid4().hex[:7]}",
        name='OOO "Snapshot"',
        legal_form="LLC",
        registration_date=date(2020, 1, 1),
        director_name="Сидоров С.С.",
        director_appointed_at=date(2021, 1, 1),
        oked_main="62.01",
        registered_address="Ташкент",
    )
    pg_session.add(borrower)
    await pg_session.flush()

    payload = {"director": "Сидоров", "amounts": [1, 2, 3]}
    snap = BorrowerSnapshotORM(
        borrower_id=borrower.id, as_of=date(2026, 1, 1), payload=payload
    )
    pg_session.add(snap)
    await pg_session.flush()

    raw = (
        await pg_session.execute(
            text("SELECT payload FROM borrower_snapshots WHERE id=:id"),
            {"id": snap.id},
        )
    ).scalar_one()
    assert isinstance(raw, dict)
    assert raw["_encrypted"] is True
    assert raw["ciphertext"].startswith("gAAAAA")

    pg_session.expire(snap, ["payload"])
    await pg_session.refresh(snap)
    assert snap.payload == payload


async def test_draft_payload_wrapped_in_jsonb(
    pg_session: AsyncSession, fernet_active: FernetPiiEncryptor
) -> None:
    payload = {"borrower": {"director_name": "Петров"}, "step": 1}
    orm = DraftORM(
        payload=payload,
        expires_at=datetime.now(tz=UTC),
    )
    pg_session.add(orm)
    await pg_session.flush()

    raw = (
        await pg_session.execute(
            text("SELECT payload FROM drafts WHERE id=:id"),
            {"id": orm.id},
        )
    ).scalar_one()
    assert raw["_encrypted"] is True

    pg_session.expire(orm, ["payload"])
    await pg_session.refresh(orm)
    assert orm.payload == payload


async def test_gnk_certificate_file_bytes_encrypted_at_rest(
    pg_session: AsyncSession, fernet_active: FernetPiiEncryptor
) -> None:
    blob = b"%PDF-1.7\n%\xc2\xa5\xc2\xb1\xc3\xab\nfake pdf content"
    orm = GnkCertificateORM(
        borrower_inn="200000001",
        full_name='OOO "GNK Test"',
        status="active",
        okveds=["62.01"],
        source="uploaded",
        file_bytes=blob,
        mime_type="application/pdf",
        file_size_bytes=len(blob),
    )
    pg_session.add(orm)
    await pg_session.flush()

    raw = (
        await pg_session.execute(
            text("SELECT file_bytes FROM gnk_certificates WHERE id=:id"),
            {"id": orm.id},
        )
    ).scalar_one()
    assert isinstance(raw, (bytes, memoryview))
    raw_bytes = bytes(raw)
    assert raw_bytes.startswith(b"gAAAAA")
    assert raw_bytes != blob

    pg_session.expire(orm, ["file_bytes"])
    await pg_session.refresh(orm)
    assert orm.file_bytes == blob
