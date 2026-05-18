"""T1.3 — PII encryption at rest (ADR-0017 / CA-DS12)

Revision ID: c5d2f3a7e1b4
Revises: b3e9f1a7d4c5
Create Date: 2026-05-18 20:00:00.000000+00:00

(1) ALTER COLUMN length expansions для Fernet token width:
    - analysts.mfa_secret  VARCHAR(64)  → VARCHAR(200)
    - analysts.full_name   VARCHAR(255) → VARCHAR(500)
    - borrowers.director_name VARCHAR(255) → VARCHAR(500)

(2) Data migration: existing plaintext → Fernet ciphertext в одной транзакции.
    Шифруются:
    - analysts.full_name + mfa_secret
    - borrowers.director_name
    - borrower_snapshots.payload (JSONB wrap {_encrypted, ciphertext})
    - drafts.payload (JSONB wrap)
    - gnk_certificates.file_bytes (BYTEA Fernet)

PII_ENC_KEYS env обязателен в production. Без него миграция выполняет
только schema-changes (length expansions) и оставляет данные plaintext —
NullPiiEncryptor fallback в приложении читает их as-is.

Idempotency: rows с `gAAAAA` prefix (string/bytes) или с `_encrypted: true`
(JSONB) пропускаются — re-run не двойной-шифрует.

Rollback: downgrade decrypt'ит обратно через тот же ключ + restore length.
БЕЗ pre-migration pg_dump переход небезопасен (потеря ключа = data loss).
См. docs/operations/pii-key-rotation.md.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c5d2f3a7e1b4"
down_revision = "b3e9f1a7d4c5"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.pii_encryption")


def _build_encryptor() -> Any | None:
    """Возвращает FernetPiiEncryptor если PII_ENC_KEYS задан, иначе None.

    None означает schema-only миграцию — data остаётся plaintext, приложение
    с NullPiiEncryptor читает её через legacy-branch TypeDecorator'а.
    """
    raw = os.environ.get("PII_ENC_KEYS", "").strip()
    if not raw:
        logger.warning(
            "PII_ENC_KEYS не задан — миграция выполняет schema-only changes. "
            "Данные останутся plaintext, приложение читает их через legacy-branch "
            "TypeDecorator'а (NullPiiEncryptor passthrough). Для prod-deploy "
            "задать PII_ENC_KEYS и re-run миграции вручную."
        )
        return None
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        return None
    from infrastructure.encryption.fernet_pii_encryptor import FernetPiiEncryptor

    return FernetPiiEncryptor(keys)


def _is_encrypted_string(value: str | None) -> bool:
    return value is not None and value.startswith("gAAAAA")


def _is_encrypted_bytes(value: bytes | None) -> bool:
    return value is not None and bytes(value).startswith(b"gAAAAA")


def _is_encrypted_jsonb(value: Any) -> bool:
    return isinstance(value, dict) and value.get("_encrypted") is True


def upgrade() -> None:
    # 1. Schema: length expansions для Fernet token width.
    op.alter_column("analysts", "mfa_secret", type_=sa.String(200))
    op.alter_column("analysts", "full_name", type_=sa.String(500))
    op.alter_column("borrowers", "director_name", type_=sa.String(500))

    # 2. Data encrypt pass.
    encryptor = _build_encryptor()
    if encryptor is None:
        return

    conn = op.get_bind()

    # analysts.full_name + mfa_secret
    rows = conn.execute(
        sa.text("SELECT id, full_name, mfa_secret FROM analysts")
    ).fetchall()
    for row in rows:
        updates: dict[str, Any] = {}
        if row.full_name and not _is_encrypted_string(row.full_name):
            updates["full_name"] = encryptor.encrypt(row.full_name)
        if row.mfa_secret and not _is_encrypted_string(row.mfa_secret):
            updates["mfa_secret"] = encryptor.encrypt(row.mfa_secret)
        if updates:
            set_clause = ", ".join(f"{k}=:{k}" for k in updates)
            conn.execute(
                sa.text(f"UPDATE analysts SET {set_clause} WHERE id=:id"),
                {**updates, "id": row.id},
            )

    # borrowers.director_name
    rows = conn.execute(
        sa.text("SELECT id, director_name FROM borrowers")
    ).fetchall()
    for row in rows:
        if row.director_name and not _is_encrypted_string(row.director_name):
            conn.execute(
                sa.text("UPDATE borrowers SET director_name=:d WHERE id=:id"),
                {"d": encryptor.encrypt(row.director_name), "id": row.id},
            )

    # borrower_snapshots.payload — wrap pattern
    rows = conn.execute(
        sa.text("SELECT id, payload FROM borrower_snapshots")
    ).fetchall()
    for row in rows:
        if _is_encrypted_jsonb(row.payload):
            continue
        plain = json.dumps(row.payload, ensure_ascii=False, default=str)
        wrapped = {"_encrypted": True, "ciphertext": encryptor.encrypt(plain)}
        conn.execute(
            sa.text(
                "UPDATE borrower_snapshots SET payload=CAST(:p AS jsonb) WHERE id=:id"
            ),
            {"p": json.dumps(wrapped), "id": row.id},
        )

    # drafts.payload — wrap pattern
    rows = conn.execute(sa.text("SELECT id, payload FROM drafts")).fetchall()
    for row in rows:
        if _is_encrypted_jsonb(row.payload):
            continue
        plain = json.dumps(row.payload, ensure_ascii=False, default=str)
        wrapped = {"_encrypted": True, "ciphertext": encryptor.encrypt(plain)}
        conn.execute(
            sa.text("UPDATE drafts SET payload=CAST(:p AS jsonb) WHERE id=:id"),
            {"p": json.dumps(wrapped), "id": row.id},
        )

    # gnk_certificates.file_bytes — Fernet binary
    rows = conn.execute(
        sa.text(
            "SELECT id, file_bytes FROM gnk_certificates WHERE file_bytes IS NOT NULL"
        )
    ).fetchall()
    for row in rows:
        blob = bytes(row.file_bytes)
        if _is_encrypted_bytes(blob):
            continue
        conn.execute(
            sa.text("UPDATE gnk_certificates SET file_bytes=:b WHERE id=:id"),
            {"b": encryptor.encrypt_bytes(blob), "id": row.id},
        )


def downgrade() -> None:
    """Rollback: decrypt data + restore VARCHAR length.

    Без PII_ENC_KEYS — schema-only: column length restore, данные остаются
    encrypt'нутыми (что эквивалентно потере ключа). Это аварийный путь.
    """
    encryptor = _build_encryptor()

    if encryptor is not None:
        conn = op.get_bind()

        # analysts: decrypt full_name + mfa_secret
        rows = conn.execute(
            sa.text("SELECT id, full_name, mfa_secret FROM analysts")
        ).fetchall()
        for row in rows:
            updates: dict[str, Any] = {}
            if row.full_name and _is_encrypted_string(row.full_name):
                updates["full_name"] = encryptor.decrypt(row.full_name)
            if row.mfa_secret and _is_encrypted_string(row.mfa_secret):
                updates["mfa_secret"] = encryptor.decrypt(row.mfa_secret)
            if updates:
                set_clause = ", ".join(f"{k}=:{k}" for k in updates)
                conn.execute(
                    sa.text(f"UPDATE analysts SET {set_clause} WHERE id=:id"),
                    {**updates, "id": row.id},
                )

        # borrowers: decrypt director_name
        rows = conn.execute(
            sa.text("SELECT id, director_name FROM borrowers")
        ).fetchall()
        for row in rows:
            if row.director_name and _is_encrypted_string(row.director_name):
                conn.execute(
                    sa.text("UPDATE borrowers SET director_name=:d WHERE id=:id"),
                    {"d": encryptor.decrypt(row.director_name), "id": row.id},
                )

        # borrower_snapshots: unwrap JSONB
        rows = conn.execute(
            sa.text("SELECT id, payload FROM borrower_snapshots")
        ).fetchall()
        for row in rows:
            if _is_encrypted_jsonb(row.payload):
                plain = json.loads(encryptor.decrypt(row.payload["ciphertext"]))
                conn.execute(
                    sa.text(
                        "UPDATE borrower_snapshots SET payload=CAST(:p AS jsonb) "
                        "WHERE id=:id"
                    ),
                    {"p": json.dumps(plain, ensure_ascii=False), "id": row.id},
                )

        # drafts: unwrap JSONB
        rows = conn.execute(sa.text("SELECT id, payload FROM drafts")).fetchall()
        for row in rows:
            if _is_encrypted_jsonb(row.payload):
                plain = json.loads(encryptor.decrypt(row.payload["ciphertext"]))
                conn.execute(
                    sa.text(
                        "UPDATE drafts SET payload=CAST(:p AS jsonb) WHERE id=:id"
                    ),
                    {"p": json.dumps(plain, ensure_ascii=False), "id": row.id},
                )

        # gnk_certificates: decrypt file_bytes
        rows = conn.execute(
            sa.text(
                "SELECT id, file_bytes FROM gnk_certificates WHERE file_bytes IS NOT NULL"
            )
        ).fetchall()
        for row in rows:
            blob = bytes(row.file_bytes)
            if _is_encrypted_bytes(blob):
                conn.execute(
                    sa.text("UPDATE gnk_certificates SET file_bytes=:b WHERE id=:id"),
                    {"b": encryptor.decrypt_bytes(blob), "id": row.id},
                )

    # Schema: restore VARCHAR length.
    op.alter_column("borrowers", "director_name", type_=sa.String(255))
    op.alter_column("analysts", "full_name", type_=sa.String(255))
    op.alter_column("analysts", "mfa_secret", type_=sa.String(64))
