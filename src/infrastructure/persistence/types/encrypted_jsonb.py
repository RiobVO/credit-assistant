"""TypeDecorator: JSONB с wrap-pattern {"_encrypted": true, "ciphertext": "..."}.

Encrypted-shape сохраняет JSONB-тип колонки (без ALTER в миграции).
Plaintext JSON сериализуется → encrypt → оборачивается в фиксированный
dict. Backward-compat: read без флага `_encrypted` возвращает payload as-is.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator

from config import encryption as _encryption  # module-import: monkeypatch-friendly

_FLAG = "_encrypted"
_FIELD = "ciphertext"


class EncryptedJsonb(TypeDecorator[dict[str, Any]]):
    impl = JSONB
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        encryptor = _encryption.get_pii_encryptor()
        if encryptor.is_passthrough:
            return value
        plain = json.dumps(value, ensure_ascii=False, default=str)
        ciphertext = encryptor.encrypt(plain)
        return {_FLAG: True, _FIELD: ciphertext}

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, dict) and value.get(_FLAG) is True:
            plain = _encryption.get_pii_encryptor().decrypt(value[_FIELD])
            return json.loads(plain)
        # Legacy plaintext payload (до миграции) — возвращаем as-is.
        return value
