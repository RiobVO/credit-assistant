"""Unit для FernetPiiEncryptor: roundtrip, multi-key rotation, ошибки."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from infrastructure.encryption.fernet_pii_encryptor import (
    EmptyPiiKeysError,
    FernetPiiEncryptor,
    InvalidPiiTokenError,
)


@pytest.fixture
def key1() -> str:
    return Fernet.generate_key().decode("ascii")


@pytest.fixture
def key2() -> str:
    return Fernet.generate_key().decode("ascii")


def test_roundtrip_string(key1: str) -> None:
    enc = FernetPiiEncryptor([key1])
    token = enc.encrypt("Иванов И.И.")
    assert token != "Иванов И.И."
    # Sentinel prefix — фиксированный для Fernet token, проверяется
    # TypeDecorator'ами для backward-compat.
    assert token.startswith("gAAAAA")
    assert enc.decrypt(token) == "Иванов И.И."


def test_roundtrip_bytes(key1: str) -> None:
    enc = FernetPiiEncryptor([key1])
    payload = b"PDF\x00binary\xff\x01\x02"
    token = enc.encrypt_bytes(payload)
    assert token != payload
    assert token.startswith(b"gAAAAA")
    assert enc.decrypt_bytes(token) == payload


def test_is_passthrough_false(key1: str) -> None:
    assert FernetPiiEncryptor([key1]).is_passthrough is False


def test_multi_key_read_with_old_key(key1: str, key2: str) -> None:
    """Rotation сценарий: token зашифрован key1 (old). После rotation
    primary становится key2, key1 уходит в read-fallback. Decrypt
    должен по-прежнему работать."""
    old_enc = FernetPiiEncryptor([key1])
    token = old_enc.encrypt("secret")

    new_enc = FernetPiiEncryptor([key2, key1])  # key2 primary, key1 fallback
    assert new_enc.decrypt(token) == "secret"


def test_writes_always_use_first_key(key1: str, key2: str) -> None:
    """Encrypt идёт первым ключом — иначе rotation не имела бы смысла."""
    new_enc = FernetPiiEncryptor([key2, key1])
    token = new_enc.encrypt("payload")

    only_new = FernetPiiEncryptor([key2])
    assert only_new.decrypt(token) == "payload"


def test_invalid_token_raises_typed_error(key1: str) -> None:
    enc = FernetPiiEncryptor([key1])
    with pytest.raises(InvalidPiiTokenError):
        enc.decrypt("not-a-valid-fernet-token")


def test_invalid_bytes_token_raises_typed_error(key1: str) -> None:
    enc = FernetPiiEncryptor([key1])
    with pytest.raises(InvalidPiiTokenError):
        enc.decrypt_bytes(b"not-a-valid-fernet-token")


def test_empty_keys_raises_at_construction() -> None:
    with pytest.raises(EmptyPiiKeysError):
        FernetPiiEncryptor([])
