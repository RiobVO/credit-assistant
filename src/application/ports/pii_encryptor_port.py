"""Protocol для PII encryption at rest (T1.3 / ADR-0017).

Используется TypeDecorator'ами (`EncryptedString` / `EncryptedJsonb` /
`EncryptedBytea`) для прозрачного encrypt/decrypt значений на ORM-уровне.

Singleton-доступ через `config.encryption.get_pii_encryptor()`.
"""

from __future__ import annotations

from typing import Protocol


class PiiEncryptorPort(Protocol):
    @property
    def is_passthrough(self) -> bool:
        """True для NullPiiEncryptor — TypeDecorator может skip JSONB-wrap."""
        ...

    def encrypt(self, plaintext: str) -> str:
        """Возвращает Fernet token (URL-safe base64). Для null — plaintext as-is."""
        ...

    def decrypt(self, ciphertext: str) -> str:
        """Расшифровывает Fernet token; raises InvalidPiiTokenError при поломке."""
        ...

    def encrypt_bytes(self, plaintext: bytes) -> bytes: ...
    def decrypt_bytes(self, ciphertext: bytes) -> bytes: ...
