"""Unit для NullPiiEncryptor — passthrough fallback."""

from __future__ import annotations

from infrastructure.encryption.null_pii_encryptor import NullPiiEncryptor


def test_is_passthrough_true() -> None:
    assert NullPiiEncryptor().is_passthrough is True


def test_encrypt_returns_plaintext_unchanged() -> None:
    enc = NullPiiEncryptor()
    assert enc.encrypt("hello") == "hello"
    assert enc.encrypt("") == ""


def test_decrypt_returns_plaintext_unchanged() -> None:
    enc = NullPiiEncryptor()
    assert enc.decrypt("hello") == "hello"


def test_encrypt_bytes_returns_bytes_unchanged() -> None:
    enc = NullPiiEncryptor()
    assert enc.encrypt_bytes(b"\x00\x01\x02") == b"\x00\x01\x02"


def test_decrypt_bytes_returns_bytes_unchanged() -> None:
    enc = NullPiiEncryptor()
    assert enc.decrypt_bytes(b"\x00\x01\x02") == b"\x00\x01\x02"
