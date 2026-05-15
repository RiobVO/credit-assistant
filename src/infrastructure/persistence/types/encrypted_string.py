"""TypeDecorator: transparent Fernet encrypt/decrypt для строковых PII-колонок.

Backward-compat: legacy plaintext-строки (без `gAAAAA` prefix) возвращаются
as-is при read'е. Это нужно для:
- запуска приложения до Alembic data-migration;
- rollback'а без encryption (downgrade без `PII_ENC_KEYS`).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.types import String, TypeDecorator

# Module-level import (не `from X import Y`) — даёт тестам возможность
# monkeypatch'нуть `_encryption.get_pii_encryptor` после импорта TypeDecorator.
from config import encryption as _encryption

# Fernet token имеет фиксированный prefix: версия (0x80 = `g`) + IV base64.
# Используется как sentinel для backward-compat.
_FERNET_PREFIX = "gAAAAA"


class EncryptedString(TypeDecorator[str]):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        return _encryption.get_pii_encryptor().encrypt(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        encryptor = _encryption.get_pii_encryptor()
        if encryptor.is_passthrough:
            return value
        # Legacy plaintext row (до миграции) — возвращаем as-is.
        if not value.startswith(_FERNET_PREFIX):
            return value
        return encryptor.decrypt(value)
