"""TypeDecorator: BYTEA с Fernet binary encrypt.

Backward-compat: legacy plain BYTEA (без `b"gAAAAA"` prefix) возвращается
as-is. Fernet token-bytes начинаются с того же sentinel что и string token
(version byte + IV в base64).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.types import TypeDecorator

from config import encryption as _encryption  # module-import: monkeypatch-friendly

_FERNET_PREFIX_BYTES = b"gAAAAA"


class EncryptedBytea(TypeDecorator[bytes]):
    impl = BYTEA
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        return _encryption.get_pii_encryptor().encrypt_bytes(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        encryptor = _encryption.get_pii_encryptor()
        if encryptor.is_passthrough:
            return value
        blob = bytes(value)
        if not blob.startswith(_FERNET_PREFIX_BYTES):
            return blob
        return encryptor.decrypt_bytes(blob)
