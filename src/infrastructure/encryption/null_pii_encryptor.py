"""Passthrough encryptor для dev без PII_ENC_KEYS (T1.3 / ADR-0017).

Активируется когда `settings.pii_enc_keys` is None/empty. Сохраняет
существующее plain-text поведение БД, чтобы:
- dev/CI baseline не требовал ключа;
- migration без `PII_ENC_KEYS` env проходила schema-only (length expansions);
- TypeDecorator работал прозрачно — `is_passthrough=True` сигнализирует
  consumers что value хранится без обёртки `_encrypted`.

В staging/prod startup-assertion в `interfaces/api/app.py` не даст приложению
запуститься с NullPiiEncryptor.
"""

from __future__ import annotations


class NullPiiEncryptor:
    is_passthrough: bool = True

    def encrypt(self, plaintext: str) -> str:
        return plaintext

    def decrypt(self, ciphertext: str) -> str:
        return ciphertext

    def encrypt_bytes(self, plaintext: bytes) -> bytes:
        return plaintext

    def decrypt_bytes(self, ciphertext: bytes) -> bytes:
        return ciphertext
