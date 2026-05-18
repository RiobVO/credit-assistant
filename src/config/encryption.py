"""Singleton factory для PII encryptor (T1.3 / ADR-0017).

Отдельный модуль, чтобы ORM-модели (`infrastructure.persistence.models.*`) и
TypeDecorator'ы могли импортировать без cycle через `interfaces/api/bank/dependencies`.

Switch logic:
- `pii_enc_keys` is None/empty → `NullPiiEncryptor` (passthrough).
- задан → `FernetPiiEncryptor` с `MultiFernet` поверх comma-separated ключей.

Singleton через `@lru_cache(maxsize=1)`. В тестах сбрасывается через
`get_pii_encryptor.cache_clear()` после monkeypatch.
"""

from __future__ import annotations

from functools import lru_cache

from application.ports.pii_encryptor_port import PiiEncryptorPort
from config.settings import get_settings
from infrastructure.encryption.fernet_pii_encryptor import FernetPiiEncryptor
from infrastructure.encryption.null_pii_encryptor import NullPiiEncryptor


@lru_cache(maxsize=1)
def get_pii_encryptor() -> PiiEncryptorPort:
    settings = get_settings()
    raw = settings.pii_enc_keys
    if not raw:
        return NullPiiEncryptor()
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        return NullPiiEncryptor()
    return FernetPiiEncryptor(keys)
