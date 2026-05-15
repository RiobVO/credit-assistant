"""MultiFernet-based PII encryptor (T1.3 / ADR-0017).

Поддерживает key rotation через `MultiFernet`:
- encrypt всегда первым (primary) ключом;
- decrypt пробует каждый ключ по порядку (новый → старый);
- при rotation: добавляем new ключ первым → deploy → re-encrypt pass →
  удаляем old ключ из env → deploy. См. docs/operations/pii-key-rotation.md.

Каждый ключ = 32-byte url-safe base64 (`Fernet.generate_key()` output).
Token имеет фиксированный prefix `gAAAAA` (version byte + IV в base64) —
используется TypeDecorator'ами как sentinel для backward-compat.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class EmptyPiiKeysError(ValueError):
    """PiiEncryptor требует хотя бы один Fernet ключ."""


class InvalidPiiTokenError(Exception):
    """Decrypt не сработал ни одним ключом из ротации.

    Возможные причины: corrupt token, неверный ключ, token зашифрован
    ключом которого больше нет в env (untracked rotation).
    """


class FernetPiiEncryptor:
    is_passthrough: bool = False

    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise EmptyPiiKeysError("at least one Fernet key required")
        fernets = [Fernet(k.encode("ascii") if isinstance(k, str) else k) for k in keys]
        self._mf = MultiFernet(fernets)

    def encrypt(self, plaintext: str) -> str:
        token = self._mf.encrypt(plaintext.encode("utf-8"))
        return token.decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._mf.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise InvalidPiiTokenError(str(exc)) from exc

    def encrypt_bytes(self, plaintext: bytes) -> bytes:
        return self._mf.encrypt(plaintext)

    def decrypt_bytes(self, ciphertext: bytes) -> bytes:
        try:
            return self._mf.decrypt(ciphertext)
        except InvalidToken as exc:
            raise InvalidPiiTokenError(str(exc)) from exc
