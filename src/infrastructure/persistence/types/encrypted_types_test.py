"""Unit для TypeDecorator'ов: bind/result через monkeypatched encryptor.

Без БД — мочим прямо `process_bind_param` / `process_result_value`.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from cryptography.fernet import Fernet
from pytest import MonkeyPatch

from config import encryption as encryption_module
from infrastructure.encryption.fernet_pii_encryptor import FernetPiiEncryptor
from infrastructure.encryption.null_pii_encryptor import NullPiiEncryptor
from infrastructure.persistence.types.encrypted_bytea import EncryptedBytea
from infrastructure.persistence.types.encrypted_jsonb import EncryptedJsonb
from infrastructure.persistence.types.encrypted_string import EncryptedString


@pytest.fixture
def fernet_enc(monkeypatch: MonkeyPatch) -> Iterator[FernetPiiEncryptor]:
    key = Fernet.generate_key().decode("ascii")
    enc = FernetPiiEncryptor([key])
    monkeypatch.setattr(encryption_module, "get_pii_encryptor", lambda: enc)
    # TypeDecorator'ы импортируют функцию by name из config.encryption,
    # поэтому patch на module-attribute достаточно.
    yield enc


@pytest.fixture
def null_enc(monkeypatch: MonkeyPatch) -> Iterator[NullPiiEncryptor]:
    enc = NullPiiEncryptor()
    monkeypatch.setattr(encryption_module, "get_pii_encryptor", lambda: enc)
    yield enc


# ── EncryptedString ─────────────────────────────────────────────────────────


def test_encrypted_string_roundtrip(fernet_enc: FernetPiiEncryptor) -> None:
    t = EncryptedString()
    bound = t.process_bind_param("Иванов", None)
    assert bound.startswith("gAAAAA")
    assert t.process_result_value(bound, None) == "Иванов"


def test_encrypted_string_passes_none(fernet_enc: FernetPiiEncryptor) -> None:
    t = EncryptedString()
    assert t.process_bind_param(None, None) is None
    assert t.process_result_value(None, None) is None


def test_encrypted_string_legacy_plain_on_read(
    fernet_enc: FernetPiiEncryptor,
) -> None:
    """Backward-compat: legacy plaintext возвращается as-is."""
    t = EncryptedString()
    assert t.process_result_value("legacy plain", None) == "legacy plain"


def test_encrypted_string_null_passthrough(null_enc: NullPiiEncryptor) -> None:
    t = EncryptedString()
    bound = t.process_bind_param("plaintext", None)
    assert bound == "plaintext"
    assert t.process_result_value(bound, None) == "plaintext"


# ── EncryptedJsonb ──────────────────────────────────────────────────────────


def test_encrypted_jsonb_roundtrip(fernet_enc: FernetPiiEncryptor) -> None:
    t = EncryptedJsonb()
    payload: dict[str, object] = {"director": "Иванов", "amounts": [1, 2]}
    bound = t.process_bind_param(payload, None)
    assert isinstance(bound, dict)
    assert bound["_encrypted"] is True
    assert isinstance(bound["ciphertext"], str)
    assert bound["ciphertext"].startswith("gAAAAA")
    assert t.process_result_value(bound, None) == payload


def test_encrypted_jsonb_legacy_plain(fernet_enc: FernetPiiEncryptor) -> None:
    """Legacy JSONB без флага `_encrypted` возвращается as-is."""
    t = EncryptedJsonb()
    assert t.process_result_value({"plain": True}, None) == {"plain": True}


def test_encrypted_jsonb_null_passthrough(null_enc: NullPiiEncryptor) -> None:
    t = EncryptedJsonb()
    payload = {"hello": "world"}
    assert t.process_bind_param(payload, None) == payload
    assert t.process_result_value(payload, None) == payload


# ── EncryptedBytea ──────────────────────────────────────────────────────────


def test_encrypted_bytea_roundtrip(fernet_enc: FernetPiiEncryptor) -> None:
    t = EncryptedBytea()
    payload = b"PDF binary \x00\xff\x01\x02"
    bound = t.process_bind_param(payload, None)
    assert bound.startswith(b"gAAAAA")
    assert t.process_result_value(bound, None) == payload


def test_encrypted_bytea_legacy_plain(fernet_enc: FernetPiiEncryptor) -> None:
    t = EncryptedBytea()
    assert t.process_result_value(b"legacy plain", None) == b"legacy plain"
