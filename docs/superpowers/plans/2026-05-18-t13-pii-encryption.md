# T1.3 PII encryption at rest (column-level через app-layer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps размечены `- [ ]`.

**Goal:** App-layer encryption для 6 PII-полей (mfa_secret, analyst.full_name, borrower.director_name, borrower_snapshots.payload, drafts.payload, gnk_certificates.file_bytes) через SQLAlchemy `TypeDecorator` + `Fernet`/`MultiFernet`. Audit log получает email-mask shared helper. ИНН, name ЮЛ, addresses, red_flags — plain (публичные / search-critical / list-view).

**Architecture:**
- Domain: `PiiEncryptorPort` (Protocol). 2 adapter'а — `FernetPiiEncryptor` (`MultiFernet` для rotation) и `NullPiiEncryptor` (passthrough, dev fallback). DI factory выбирает по `settings.pii_enc_keys`.
- SQLAlchemy `TypeDecorator`: `EncryptedString`, `EncryptedJsonb` (wrap pattern `{"_encrypted": true, "ciphertext": "..."}`), `EncryptedBytea`. Все три дёргают `get_pii_encryptor()` singleton при bind/result.
- Audit-log shared helper `mask_email` в `infrastructure/auth/email_mask.py` — вынос из `bank/mfa.py:59`. Подменяет `_mask_email` там же. 2 callsite-фикса в `authenticate_analyst.py:53` и `admin.py:77`.
- Alembic migration: (1) ALTER COLUMN length expansions (`mfa_secret` 64→200, `analysts.full_name` 255→500, `borrowers.director_name` 255→500). (2) Data migration: read plaintext → Python encrypt → write ciphertext. (3) JSONB-wrap для snapshots.payload + drafts.payload. (4) BYTEA encrypt для gnk_certificates.file_bytes (если есть данные — сейчас 0 строк).
- Backward-compat read: `EncryptedJsonb.process_result_value` смотрит флаг `_encrypted`. Если нет — legacy plain (для записей до миграции / при downgrade без data re-decrypt).
- Production assertion: `if app_env in ("staging","prod") and not pii_enc_keys: crash on startup`.

**Master key:**
- `PII_ENC_KEYS` env (comma-separated). Первый — primary (write), остальные — read fallback. Каждый ключ = 32-byte url-safe base64 (`Fernet.generate_key()` output).
- При rotation: добавляем new ключ в начало, deploy → re-encrypt pass → old ключ удаляется из env.

**Tech Stack:** `cryptography>=42` (`Fernet`/`MultiFernet`/`InvalidToken`), SQLAlchemy 2.0 `TypeDecorator`, Alembic data migration.

**Commit policy:** Single atomic commit в конце (после Phase 11 verify). Within phases TDD.

**Pre-condition:** `pg_dump credit_assistant > backup-pre-t13.sql` mandatory до runs миграции в prod (runbook в `docs/operations/pii-key-rotation.md`).

**Frozen scope** (не trogal):
- Blind-index для INN (rejected: ИНН публичный).
- pgcrypto/transparent disk encryption (ops-level, не app).
- LDAP/OAuth (T1.5).
- Multi-tenant runtime isolation (T1.4).

---

## File Structure

**Backend — новые:**
- `src/application/ports/pii_encryptor_port.py` — `PiiEncryptorPort` Protocol.
- `src/infrastructure/encryption/null_pii_encryptor.py` — passthrough.
- `src/infrastructure/encryption/null_pii_encryptor_test.py` — unit.
- `src/infrastructure/encryption/fernet_pii_encryptor.py` — `MultiFernet` adapter.
- `src/infrastructure/encryption/fernet_pii_encryptor_test.py` — unit (roundtrip + rotation + invalid).
- `src/infrastructure/encryption/__init__.py`
- `src/infrastructure/persistence/types/encrypted_string.py` — TypeDecorator(String).
- `src/infrastructure/persistence/types/encrypted_jsonb.py` — TypeDecorator(JSONB), wrap pattern.
- `src/infrastructure/persistence/types/encrypted_bytea.py` — TypeDecorator(BYTEA).
- `src/infrastructure/persistence/types/__init__.py`
- `src/infrastructure/persistence/types/encrypted_types_test.py` — unit.
- `src/infrastructure/auth/email_mask.py` — shared `mask_email(email: str) -> str`.
- `src/infrastructure/auth/email_mask_test.py` — unit.
- `src/infrastructure/persistence/migrations/versions/20260518_2000_pii_encryption.py` — Alembic.

**Backend — modify:**
- `pyproject.toml` — `cryptography>=42`.
- `src/config/settings.py` — `pii_enc_keys: str | None = None` + post-init prod assertion.
- `.env.example` — `PII_ENC_KEYS=`.
- `docker-compose.yml` — `PII_ENC_KEYS: ${PII_ENC_KEYS:-}` (пусто → NullPiiEncryptor в dev compose; для compose dev можно сгенерить тестовый ключ).
- `src/infrastructure/persistence/models/analyst.py` — `mfa_secret` → `EncryptedString(200)`, `full_name` → `EncryptedString(500)`.
- `src/infrastructure/persistence/models/borrower.py` — `director_name` → `EncryptedString(500)`.
- `src/infrastructure/persistence/models/borrower_snapshot.py` — `payload` → `EncryptedJsonb`.
- `src/infrastructure/persistence/models/draft.py` — `payload` → `EncryptedJsonb`.
- `src/infrastructure/persistence/models/gnk_certificate.py` — `file_bytes` → `EncryptedBytea` (nullable).
- `src/interfaces/api/bank/dependencies.py` — `get_pii_encryptor()` factory с `@lru_cache(maxsize=1)` (или в shared `config/encryption.py` ради import-cycle hygiene).
- `src/interfaces/api/app.py` — startup assertion для prod env.
- `src/interfaces/api/bank/mfa.py` — заменить `_mask_email` на shared `mask_email`.
- `src/application/use_cases/authenticate_analyst.py:53` — `email` → `mask_email(email)` в payload.
- `src/interfaces/api/bank/admin.py:77` — `target_email` → `mask_email(orm.email)`.

**Backend — tests modify** (round-trip с encrypted columns, integration не должен сломаться):
- `src/infrastructure/persistence/mappers/analyst_mapper_test.py` — может потребовать pii_encryptor fixture autouse.
- `src/infrastructure/persistence/mappers/snapshot_mapper_test.py` — то же.
- Integration tests `tests/integration/persistence/borrower_repository_test.py`, `snapshot_dossier_repository_test.py`, `gnk_certificate_repository_test.py`, `draft_test.py` — могут требовать fixture.

**Tests новые:**
- `tests/integration/persistence/pii_encryption_roundtrip_test.py` — integration (testcontainers): INSERT plaintext через ORM → raw SELECT (ciphertext) → ORM SELECT (decrypted). 5 cases на 5 типов колонок.

**Docs:**
- `docs/adr/0017-pii-encryption-at-rest.md` — новый ADR.
- `docs/operations/pii-key-rotation.md` — runbook: generate key, deploy add to PII_ENC_KEYS, re-encrypt script, remove old.
- `CLAUDE.md` — Current Status T1.3 → DONE, T1.4 active. Раздел Persistence: PII encryption convention.
- `docs/pre-demo-roadmap.md` — T1.3 → DONE с commit hash.

---

## Task 1: Dependencies + Settings + Compose + Startup assertion

**Files:** `pyproject.toml`, `src/config/settings.py`, `.env.example`, `docker-compose.yml`, `src/interfaces/api/app.py`

- [ ] **Step 1.1: pyproject.toml** — `cryptography>=42` в `[project.dependencies]`. uv lock на хосте.

- [ ] **Step 1.2: settings.py** — добавить:
```python
# T1.3 (CA-019/CA-DS12): comma-separated Fernet keys. Первый — primary (write),
# остальные — read fallback для rotation. Каждый ключ = 32-byte url-safe base64.
# None в dev → NullPiiEncryptor (passthrough). В staging/prod startup-assert требует
# хотя бы один ключ. См. ADR-0017 + docs/operations/pii-key-rotation.md.
pii_enc_keys: str | None = None
```

- [ ] **Step 1.3: .env.example** — добавить:
```
# T1.3 PII encryption (ADR-0017): comma-separated Fernet keys (32-byte url-safe base64).
# Пустое — NullPiiEncryptor fallback (только dev). Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
PII_ENC_KEYS=
```

- [ ] **Step 1.4: docker-compose.yml** — `PII_ENC_KEYS: ${PII_ENC_KEYS:-}` в api.environment. Comment про generation.

- [ ] **Step 1.5: app.py startup** — assertion в `create_app`:
```python
if settings.app_env in ("staging", "prod") and not settings.pii_enc_keys:
    raise RuntimeError(
        "PII_ENC_KEYS обязателен в staging/prod (T1.3 / ADR-0017). "
        "Generate: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )
```

- [ ] **Step 1.6 (Verify):** `uv lock && docker compose up -d --build api && docker compose exec api uv run python -c "from cryptography.fernet import Fernet, MultiFernet; print('OK')"`.

---

## Task 2: PiiEncryptorPort + NullPiiEncryptor (TDD)

**Files:**
- Create: `src/application/ports/pii_encryptor_port.py`
- Create: `src/infrastructure/encryption/__init__.py`
- Create: `src/infrastructure/encryption/null_pii_encryptor.py`
- Create: `src/infrastructure/encryption/null_pii_encryptor_test.py`

- [ ] **Step 2.1 (Red): null_pii_encryptor_test.py**
```python
import pytest
from infrastructure.encryption.null_pii_encryptor import NullPiiEncryptor


@pytest.fixture
def encryptor():
    return NullPiiEncryptor()


def test_encrypt_returns_plaintext_unchanged(encryptor):
    assert encryptor.encrypt("hello") == "hello"
    assert encryptor.encrypt("") == ""


def test_decrypt_returns_plaintext_unchanged(encryptor):
    assert encryptor.decrypt("hello") == "hello"


def test_encrypt_bytes_returns_bytes_unchanged(encryptor):
    assert encryptor.encrypt_bytes(b"\x00\x01\x02") == b"\x00\x01\x02"


def test_decrypt_bytes_returns_bytes_unchanged(encryptor):
    assert encryptor.decrypt_bytes(b"\x00\x01\x02") == b"\x00\x01\x02"


def test_is_passthrough_true(encryptor):
    assert encryptor.is_passthrough is True
```

- [ ] **Step 2.2 (Green): pii_encryptor_port.py**
```python
"""Protocol для PII encryption at rest (T1.3 / ADR-0017)."""
from __future__ import annotations
from typing import Protocol


class PiiEncryptorPort(Protocol):
    @property
    def is_passthrough(self) -> bool:
        """True для NullPiiEncryptor — TypeDecorator может skip JSONB-wrap."""
        ...

    def encrypt(self, plaintext: str) -> str: ...
    def decrypt(self, ciphertext: str) -> str: ...
    def encrypt_bytes(self, plaintext: bytes) -> bytes: ...
    def decrypt_bytes(self, ciphertext: bytes) -> bytes: ...
```

- [ ] **Step 2.3 (Green): null_pii_encryptor.py**
```python
"""Passthrough encryptor для dev без PII_ENC_KEYS (T1.3 / ADR-0017)."""
from __future__ import annotations


class NullPiiEncryptor:
    is_passthrough = True

    def encrypt(self, plaintext: str) -> str:
        return plaintext

    def decrypt(self, ciphertext: str) -> str:
        return ciphertext

    def encrypt_bytes(self, plaintext: bytes) -> bytes:
        return plaintext

    def decrypt_bytes(self, ciphertext: bytes) -> bytes:
        return ciphertext
```

- [ ] **Step 2.4 (Verify):** `pytest src/infrastructure/encryption/null_pii_encryptor_test.py -v` → 5 green.

---

## Task 3: FernetPiiEncryptor + MultiFernet (TDD)

**Files:**
- Create: `src/infrastructure/encryption/fernet_pii_encryptor.py`
- Create: `src/infrastructure/encryption/fernet_pii_encryptor_test.py`

- [ ] **Step 3.1 (Red): unit tests**
```python
import pytest
from cryptography.fernet import Fernet
from infrastructure.encryption.fernet_pii_encryptor import (
    FernetPiiEncryptor, InvalidPiiTokenError, EmptyPiiKeysError,
)


@pytest.fixture
def key1() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture
def key2() -> str:
    return Fernet.generate_key().decode()


def test_roundtrip_string(key1):
    enc = FernetPiiEncryptor([key1])
    token = enc.encrypt("Иванов И.И.")
    assert token != "Иванов И.И."
    assert enc.decrypt(token) == "Иванов И.И."


def test_roundtrip_bytes(key1):
    enc = FernetPiiEncryptor([key1])
    payload = b"PDF\x00binary\xff"
    token = enc.encrypt_bytes(payload)
    assert token != payload
    assert enc.decrypt_bytes(token) == payload


def test_is_passthrough_false(key1):
    assert FernetPiiEncryptor([key1]).is_passthrough is False


def test_multi_key_read_with_old_key(key1, key2):
    """Rotation: token зашифрован key1 (old), затем new key prepended."""
    old_enc = FernetPiiEncryptor([key1])
    token = old_enc.encrypt("secret")
    new_enc = FernetPiiEncryptor([key2, key1])  # key2 new primary
    assert new_enc.decrypt(token) == "secret"


def test_writes_always_use_first_key(key1, key2):
    new_enc = FernetPiiEncryptor([key2, key1])
    token = new_enc.encrypt("payload")
    # Decrypt с одним key2 — должен сработать.
    only_new = FernetPiiEncryptor([key2])
    assert only_new.decrypt(token) == "payload"


def test_invalid_token_raises(key1):
    enc = FernetPiiEncryptor([key1])
    with pytest.raises(InvalidPiiTokenError):
        enc.decrypt("not-a-valid-fernet-token")


def test_empty_keys_raises():
    with pytest.raises(EmptyPiiKeysError):
        FernetPiiEncryptor([])
```

- [ ] **Step 3.2 (Green): fernet_pii_encryptor.py**
```python
"""MultiFernet-based PII encryptor (T1.3 / ADR-0017).

Rotation: первый ключ — primary (write), остальные — read fallback.
Encrypt всегда первым ключом; decrypt пытается каждый по порядку.
"""
from __future__ import annotations
from cryptography.fernet import Fernet, InvalidToken, MultiFernet


class EmptyPiiKeysError(ValueError):
    """PiiEncryptor требует хотя бы один ключ."""


class InvalidPiiTokenError(Exception):
    """Decrypt не сработал ни одним ключом из ротации."""


class FernetPiiEncryptor:
    is_passthrough = False

    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise EmptyPiiKeysError("at least one Fernet key required")
        fernets = [Fernet(k.encode() if isinstance(k, str) else k) for k in keys]
        self._mf = MultiFernet(fernets)

    def encrypt(self, plaintext: str) -> str:
        return self._mf.encrypt(plaintext.encode("utf-8")).decode("ascii")

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
```

- [ ] **Step 3.3 (Verify):** `pytest src/infrastructure/encryption/fernet_pii_encryptor_test.py -v` → 7 green.

---

## Task 4: DI factory + production assertion

**Files:** `src/interfaces/api/bank/dependencies.py` (или новый `src/config/encryption.py` для import-cycle hygiene).

- [ ] **Step 4.1: factory**
```python
# src/config/encryption.py — отдельный модуль, чтобы ORM-модели могли импортировать
# без cycle через bank/dependencies.
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
    return FernetPiiEncryptor(keys)
```

- [ ] **Step 4.2: app.py startup assertion** — `if settings.app_env in ("staging","prod") and not settings.pii_enc_keys: raise RuntimeError(...)`.

- [ ] **Step 4.3 (Verify):** `uv run python -c "from config.encryption import get_pii_encryptor; print(type(get_pii_encryptor()).__name__)"` → `NullPiiEncryptor` (без env). С `PII_ENC_KEYS=<key>` env → `FernetPiiEncryptor`.

---

## Task 5: SQLAlchemy TypeDecorator (3 типа) + unit tests

**Files:**
- Create: `src/infrastructure/persistence/types/__init__.py`
- Create: `src/infrastructure/persistence/types/encrypted_string.py`
- Create: `src/infrastructure/persistence/types/encrypted_jsonb.py`
- Create: `src/infrastructure/persistence/types/encrypted_bytea.py`
- Create: `src/infrastructure/persistence/types/encrypted_types_test.py`

- [ ] **Step 5.1: encrypted_string.py**
```python
"""TypeDecorator: transparent Fernet encrypt/decrypt для строковых PII-колонок."""
from __future__ import annotations
from typing import Any
from sqlalchemy.types import String, TypeDecorator
from config.encryption import get_pii_encryptor


class EncryptedString(TypeDecorator[str]):
    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        return get_pii_encryptor().encrypt(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        encryptor = get_pii_encryptor()
        if encryptor.is_passthrough:
            return value
        # Legacy plain-text row до миграции / rollback — Fernet token имеет
        # фиксированный формат (начинается с `gAAAAA`). Если префикс не тот —
        # возвращаем as-is (backward-compat).
        if not value.startswith("gAAAAA"):
            return value
        return encryptor.decrypt(value)
```

- [ ] **Step 5.2: encrypted_jsonb.py**
```python
"""TypeDecorator: JSONB с wrap-pattern {"_encrypted": true, "ciphertext": "..."}."""
from __future__ import annotations
import json
from typing import Any
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator
from config.encryption import get_pii_encryptor

_FLAG = "_encrypted"


class EncryptedJsonb(TypeDecorator[dict[str, Any]]):
    impl = JSONB
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        encryptor = get_pii_encryptor()
        if encryptor.is_passthrough:
            return value
        ciphertext = encryptor.encrypt(json.dumps(value, ensure_ascii=False, default=str))
        return {_FLAG: True, "ciphertext": ciphertext}

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, dict) and value.get(_FLAG) is True:
            plaintext = get_pii_encryptor().decrypt(value["ciphertext"])
            return json.loads(plaintext)
        return value  # legacy plain payload — backward-compat
```

- [ ] **Step 5.3: encrypted_bytea.py**
```python
"""TypeDecorator: BYTEA с Fernet binary encrypt."""
from __future__ import annotations
from typing import Any
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.types import TypeDecorator
from config.encryption import get_pii_encryptor


class EncryptedBytea(TypeDecorator[bytes]):
    impl = BYTEA
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        return get_pii_encryptor().encrypt_bytes(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        encryptor = get_pii_encryptor()
        if encryptor.is_passthrough:
            return value
        if not value.startswith(b"gAAAAA"):
            return value  # legacy plain
        return encryptor.decrypt_bytes(bytes(value))
```

- [ ] **Step 5.4 (Red): encrypted_types_test.py** — unit-тесты без БД (мочим TypeDecorator через `process_*_param`/`process_result_value`):
```python
import pytest
from cryptography.fernet import Fernet
from config.encryption import get_pii_encryptor
from infrastructure.encryption.fernet_pii_encryptor import FernetPiiEncryptor
from infrastructure.encryption.null_pii_encryptor import NullPiiEncryptor
from infrastructure.persistence.types.encrypted_string import EncryptedString
from infrastructure.persistence.types.encrypted_jsonb import EncryptedJsonb
from infrastructure.persistence.types.encrypted_bytea import EncryptedBytea


@pytest.fixture
def with_fernet(monkeypatch):
    key = Fernet.generate_key().decode()
    enc = FernetPiiEncryptor([key])
    monkeypatch.setattr(
        "config.encryption.get_pii_encryptor",
        lambda: enc,
    )
    get_pii_encryptor.cache_clear()
    yield enc
    get_pii_encryptor.cache_clear()


@pytest.fixture
def with_null(monkeypatch):
    enc = NullPiiEncryptor()
    monkeypatch.setattr("config.encryption.get_pii_encryptor", lambda: enc)
    get_pii_encryptor.cache_clear()
    yield enc
    get_pii_encryptor.cache_clear()


def test_encrypted_string_roundtrip(with_fernet):
    t = EncryptedString()
    bound = t.process_bind_param("Иванов", None)
    assert bound.startswith("gAAAAA")
    assert t.process_result_value(bound, None) == "Иванов"


def test_encrypted_string_passes_none(with_fernet):
    t = EncryptedString()
    assert t.process_bind_param(None, None) is None
    assert t.process_result_value(None, None) is None


def test_encrypted_string_legacy_plain_on_read(with_fernet):
    """Backward-compat: row до миграции возвращается as-is."""
    t = EncryptedString()
    assert t.process_result_value("legacy plain", None) == "legacy plain"


def test_encrypted_string_null_passthrough(with_null):
    t = EncryptedString()
    bound = t.process_bind_param("plaintext", None)
    assert bound == "plaintext"
    assert t.process_result_value(bound, None) == "plaintext"


def test_encrypted_jsonb_roundtrip(with_fernet):
    t = EncryptedJsonb()
    payload = {"director": "Иванов", "amounts": [1, 2]}
    bound = t.process_bind_param(payload, None)
    assert bound == {"_encrypted": True, "ciphertext": bound["ciphertext"]}
    assert t.process_result_value(bound, None) == payload


def test_encrypted_jsonb_legacy_plain(with_fernet):
    """Legacy row без флага `_encrypted` возвращается as-is."""
    t = EncryptedJsonb()
    assert t.process_result_value({"plain": True}, None) == {"plain": True}


def test_encrypted_jsonb_null_passthrough(with_null):
    t = EncryptedJsonb()
    payload = {"hello": "world"}
    assert t.process_bind_param(payload, None) == payload
    assert t.process_result_value(payload, None) == payload


def test_encrypted_bytea_roundtrip(with_fernet):
    t = EncryptedBytea()
    payload = b"PDF binary \x00\xff"
    bound = t.process_bind_param(payload, None)
    assert bound.startswith(b"gAAAAA")
    assert t.process_result_value(bound, None) == payload


def test_encrypted_bytea_legacy_plain(with_fernet):
    t = EncryptedBytea()
    assert t.process_result_value(b"legacy plain", None) == b"legacy plain"
```

- [ ] **Step 5.5 (Verify):** `pytest src/infrastructure/persistence/types/encrypted_types_test.py -v` → 9 green.

---

## Task 6: ORM column modifications

**Files (modify):**
- `src/infrastructure/persistence/models/analyst.py` — `mfa_secret: EncryptedString(200)`, `full_name: EncryptedString(500)`.
- `src/infrastructure/persistence/models/borrower.py` — `director_name: EncryptedString(500)`.
- `src/infrastructure/persistence/models/borrower_snapshot.py` — `payload: EncryptedJsonb`.
- `src/infrastructure/persistence/models/draft.py` — `payload: EncryptedJsonb`.
- `src/infrastructure/persistence/models/gnk_certificate.py` — `file_bytes: EncryptedBytea`.

Тип `Mapped[str]` остаётся (TypeDecorator transparent). Length-параметры VARCHAR обновляются под Fernet token width.

**Backward-compat:** существующая БД ещё держит plain — миграция (Task 7) проведёт re-encrypt. До миграции read с `gAAAAA` префиксом decrypt'ится, без — возвращается plain (легаси).

- [ ] **Step 6.1:** обновить 5 файлов.

- [ ] **Step 6.2 (Verify):** `uv run python -c "from infrastructure.persistence.models import analyst, borrower, borrower_snapshot, draft, gnk_certificate; print('OK')"`.

---

## Task 7: Alembic migration (schema length + data encrypt)

**Files:**
- Create: `src/infrastructure/persistence/migrations/versions/20260518_2000_pii_encryption.py`

**Logic:**
1. ALTER TABLE для length expansions (3 колонки).
2. Если `PII_ENC_KEYS` не задан в migration env → log warning, skip data pass (dev migration без encrypt).
3. Если задан → build encryptor, SELECT plaintext, encrypt, UPDATE.
4. Для JSONB-payloads: SELECT plain dict → wrap в `{_encrypted, ciphertext}` → UPDATE.

- [ ] **Step 7.1: migration body**
```python
"""T1.3 PII encryption at rest (CA-DS12 / ADR-0017)

Revision ID: c5d2f3a7e1b4
Revises: b3e9f1a7d4c5
Create Date: 2026-05-18 20:00:00.000000+00:00

(1) ALTER COLUMN length expansions для Fernet token width.
(2) Data migration: existing plaintext → Fernet ciphertext в одной транзакции.
    Requires PII_ENC_KEYS env (или dev skip flag).

Rollback: downgrade decrypt'ит обратно через тот же ключ.
БЕЗ pre-migration pg_dump переход небезопасен (потеря ключа = потеря данных).
См. docs/operations/pii-key-rotation.md.
"""
from alembic import op
import json
import os
import sqlalchemy as sa

revision = "c5d2f3a7e1b4"
down_revision = "b3e9f1a7d4c5"


def _get_encryptor():
    keys_env = os.environ.get("PII_ENC_KEYS", "").strip()
    if not keys_env:
        return None  # skip data encrypt (dev)
    from infrastructure.encryption.fernet_pii_encryptor import FernetPiiEncryptor
    keys = [k.strip() for k in keys_env.split(",") if k.strip()]
    return FernetPiiEncryptor(keys)


def upgrade():
    # 1. Length expansions
    op.alter_column("analysts", "mfa_secret", type_=sa.String(200))
    op.alter_column("analysts", "full_name", type_=sa.String(500))
    op.alter_column("borrowers", "director_name", type_=sa.String(500))

    # 2. Data encrypt pass
    encryptor = _get_encryptor()
    if encryptor is None:
        # Dev/test без PII_ENC_KEYS — schema-only migration. Production обязан
        # задать ключ (см. startup assertion).
        return

    conn = op.get_bind()

    # analysts.full_name + mfa_secret
    rows = conn.execute(sa.text(
        "SELECT id, full_name, mfa_secret FROM analysts"
    )).fetchall()
    for row in rows:
        full = encryptor.encrypt(row.full_name) if row.full_name else None
        secret = encryptor.encrypt(row.mfa_secret) if row.mfa_secret else None
        conn.execute(
            sa.text(
                "UPDATE analysts SET full_name=:f, mfa_secret=:s WHERE id=:id"
            ),
            {"f": full, "s": secret, "id": row.id},
        )

    # borrowers.director_name
    rows = conn.execute(sa.text("SELECT id, director_name FROM borrowers")).fetchall()
    for row in rows:
        if row.director_name:
            enc = encryptor.encrypt(row.director_name)
            conn.execute(
                sa.text("UPDATE borrowers SET director_name=:d WHERE id=:id"),
                {"d": enc, "id": row.id},
            )

    # borrower_snapshots.payload — wrap pattern
    rows = conn.execute(sa.text("SELECT id, payload FROM borrower_snapshots")).fetchall()
    for row in rows:
        payload = row.payload  # уже dict (JSONB)
        if isinstance(payload, dict) and payload.get("_encrypted") is True:
            continue
        ciphertext = encryptor.encrypt(json.dumps(payload, ensure_ascii=False, default=str))
        wrapped = {"_encrypted": True, "ciphertext": ciphertext}
        conn.execute(
            sa.text("UPDATE borrower_snapshots SET payload=cast(:p AS jsonb) WHERE id=:id"),
            {"p": json.dumps(wrapped), "id": row.id},
        )

    # drafts.payload — wrap pattern
    rows = conn.execute(sa.text("SELECT id, payload FROM drafts")).fetchall()
    for row in rows:
        payload = row.payload
        if isinstance(payload, dict) and payload.get("_encrypted") is True:
            continue
        ciphertext = encryptor.encrypt(json.dumps(payload, ensure_ascii=False, default=str))
        wrapped = {"_encrypted": True, "ciphertext": ciphertext}
        conn.execute(
            sa.text("UPDATE drafts SET payload=cast(:p AS jsonb) WHERE id=:id"),
            {"p": json.dumps(wrapped), "id": row.id},
        )

    # gnk_certificates.file_bytes — binary
    rows = conn.execute(sa.text(
        "SELECT id, file_bytes FROM gnk_certificates WHERE file_bytes IS NOT NULL"
    )).fetchall()
    for row in rows:
        blob = bytes(row.file_bytes)
        if blob.startswith(b"gAAAAA"):
            continue
        enc = encryptor.encrypt_bytes(blob)
        conn.execute(
            sa.text("UPDATE gnk_certificates SET file_bytes=:b WHERE id=:id"),
            {"b": enc, "id": row.id},
        )


def downgrade():
    """Rollback: decrypt обратно и restore length."""
    encryptor = _get_encryptor()
    if encryptor is None:
        # Without keys — schema-only rollback (data остаётся encrypt'нутым).
        op.alter_column("borrowers", "director_name", type_=sa.String(255))
        op.alter_column("analysts", "full_name", type_=sa.String(255))
        op.alter_column("analysts", "mfa_secret", type_=sa.String(64))
        return

    conn = op.get_bind()
    # Inverse data pass — decrypt everything back to plain.
    # ... (зеркало upgrade с .decrypt вместо .encrypt)

    op.alter_column("borrowers", "director_name", type_=sa.String(255))
    op.alter_column("analysts", "full_name", type_=sa.String(255))
    op.alter_column("analysts", "mfa_secret", type_=sa.String(64))
```

- [ ] **Step 7.2 (Verify):** генерим test key, прогоняем `PII_ENC_KEYS=<key> alembic upgrade head` → 12 borrowers, 49 snapshots, 48 drafts, 2 analysts перешифровались. Затем `alembic downgrade -1` → restored. Затем `alembic upgrade head` повторно (idempotent).

---

## Task 8: Email mask shared helper

**Files:**
- Create: `src/infrastructure/auth/email_mask.py`
- Create: `src/infrastructure/auth/email_mask_test.py`
- Modify: `src/interfaces/api/bank/mfa.py` (drop local `_mask_email`, import shared).
- Modify: `src/application/use_cases/authenticate_analyst.py` — `payload={"email": mask_email(email), "ip": ip}`.
- Modify: `src/interfaces/api/bank/admin.py:77` — `target_email: mask_email(orm.email)`.

- [ ] **Step 8.1 (Red): email_mask_test.py**
```python
from infrastructure.auth.email_mask import mask_email


def test_mask_email_keeps_first_two_chars():
    assert mask_email("ivanov@bank.uz") == "iv***@bank.uz"


def test_mask_email_short_local():
    assert mask_email("a@b.uz") == "a***@b.uz"


def test_mask_email_no_at():
    assert mask_email("garbage") == "***"


def test_mask_email_empty():
    assert mask_email("") == "***"
```

- [ ] **Step 8.2 (Green): email_mask.py**
```python
"""Audit-friendly email masking — local-part truncated to first 2 chars."""
from __future__ import annotations


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[:2]}***@{domain}"
```

- [ ] **Step 8.3: 3 callsite swaps** — bank/mfa.py (drop `_mask_email`, import + use shared), authenticate_analyst.py, admin.py.

- [ ] **Step 8.4 (Verify):** unit-tests + grep `_mask_email` → пусто, `mask_email` → 3+ callsites.

---

## Task 9: Integration test — encryption roundtrip против real Postgres

**Files:**
- Create: `tests/integration/persistence/pii_encryption_roundtrip_test.py`

- [ ] **Step 9.1: integration test**
```python
"""Integration: ORM read/write через EncryptedString/Jsonb/Bytea — данные
шифруются в БД и расшифровываются обратно прозрачно."""
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.encryption import get_pii_encryptor
from infrastructure.persistence.models.analyst import AnalystORM
# ... etc

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def with_fernet_encryptor(monkeypatch):
    """Запатчить factory: тест видит FernetPiiEncryptor."""
    from infrastructure.encryption.fernet_pii_encryptor import FernetPiiEncryptor
    key = Fernet.generate_key().decode()
    enc = FernetPiiEncryptor([key])
    monkeypatch.setattr("config.encryption.get_pii_encryptor", lambda: enc)
    get_pii_encryptor.cache_clear()
    yield enc
    get_pii_encryptor.cache_clear()


async def test_analyst_full_name_encrypted_at_rest(
    pg_session: AsyncSession, with_fernet_encryptor
):
    orm = AnalystORM(
        email="encrypt-test@bank.uz",
        password_hash="$2b$04$abc",
        full_name="Иванов И.И.",
        role="analyst",
        is_active=True,
    )
    pg_session.add(orm)
    await pg_session.flush()
    analyst_id = orm.id

    # Raw query — full_name должен быть Fernet token (не plain).
    raw = (await pg_session.execute(
        text("SELECT full_name FROM analysts WHERE id=:id"),
        {"id": analyst_id},
    )).scalar_one()
    assert raw != "Иванов И.И."
    assert raw.startswith("gAAAAA")

    # ORM SELECT — transparent decrypt.
    await pg_session.expire(orm, ["full_name"])
    await pg_session.refresh(orm)
    assert orm.full_name == "Иванов И.И."


# Аналогичные тесты:
# - test_borrower_director_name_encrypted_at_rest
# - test_snapshot_payload_wrapped_in_jsonb
# - test_draft_payload_wrapped_in_jsonb
# - test_gnk_file_bytes_encrypted_at_rest
```

- [ ] **Step 9.2 (Verify):** на хосте `PYTHONPATH=src uv run pytest tests/integration/persistence/pii_encryption_roundtrip_test.py -v -m integration` → 5 green.

---

## Task 10: Existing tests fixture — autouse decryptor

**Why:** существующие `bank_search_test`, `borrower_repository_test`, etc. могут упасть если в conftest нет patch на `get_pii_encryptor`. По умолчанию `NullPiiEncryptor` — что значит plain. Тесты должны продолжать работать.

Однако: settings default `pii_enc_keys=None` → factory вернёт `NullPiiEncryptor` → bind/result passthrough → bind тестов идентичен старому. **Тесты НЕ должны падать**, если фабрика правильно срабатывает.

- [ ] **Step 10.1:** прогнать **полный** integration suite без правок conftest, посмотреть фактический baseline.

- [ ] **Step 10.2:** если что-то падает — добавить `autouse cache_clear` в `tests/integration/conftest.py`:
```python
@pytest.fixture(autouse=True)
def _clear_pii_cache():
    get_pii_encryptor.cache_clear()
    yield
    get_pii_encryptor.cache_clear()
```

- [ ] **Step 10.3 (Verify):** `pytest tests/integration -v -m integration` → все integration green.

---

## Task 11: ADR-0017 + runbook + CLAUDE.md + roadmap

**Files:**
- Create: `docs/adr/0017-pii-encryption-at-rest.md`
- Create: `docs/operations/pii-key-rotation.md`
- Modify: `CLAUDE.md` — Current Status T1.3 closed, T1.4 active. Persistence section + PII convention.
- Modify: `docs/pre-demo-roadmap.md` — T1.3 → DONE.

ADR-0017 sections:
- **Context:** stolen-backup / dump-leak threat model. Compliance ПДн Узбекистана (Закон №547).
- **Decision:** per-column app-layer encrypt через `Fernet` + `MultiFernet`. ИНН/name plain (публичные). Mask audit emails.
- **Alternatives:** pgcrypto (transparent disk), full-row encrypt, blind-index INN.
- **Trade-offs:** ключ-loss = data-loss; key-rotation runbook; Fernet token width.
- **Security checklist:** key generation, env management, pre-migration backup, rollback safety.

Runbook sections (key rotation):
1. Generate new key.
2. Add to env как первый: `PII_ENC_KEYS=<new>,<old>`. Deploy.
3. Run re-encrypt script `python -m interfaces.cli.rotate_pii_keys` (proxy через MultiFernet `.rotate()`).
4. Remove old key from env. Deploy.

- [ ] **Step 11.1-4:** написать 4 файла.

---

## Task 12: Final verify + commit + push

- [ ] **Step 12.1:** `gh run list --branch main -L 3` — baseline green.
- [ ] **Step 12.2:** `uv run ruff check . && uv run mypy --strict src tests && uv run pytest -q` — all green.
- [ ] **Step 12.3:** `cd web && npm run lint && npm run test:run && npx tsc --noEmit && npm run build` — frontend не trogal но проверка зеркало T1.2.
- [ ] **Step 12.4:** E2E smoke:
  ```
  # Generate test key
  KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  # Restart api with key
  PII_ENC_KEYS=$KEY APP_MODE=bank docker compose up -d --build api
  # Login → fetch /me → full_name decrypted транспарентно
  # Raw SQL → ciphertext
  docker compose exec -T postgres psql -U credit -d credit_assistant -c \
    "SELECT email, substring(full_name FOR 30) FROM analysts WHERE email='t04@bank.uz'"
  # Expect: full_name начинается с gAAAAA
  ```
- [ ] **Step 12.5:** atomic commit:
  ```
  feat(security): T1.3 PII encryption at rest (CA-DS12 / ADR-0017)

  - PiiEncryptorPort + FernetPiiEncryptor (MultiFernet rotation) + Null fallback.
  - SQLAlchemy TypeDecorator: EncryptedString/Jsonb/Bytea — transparent на ORM.
  - 6 PII columns: analysts.{full_name, mfa_secret}, borrowers.director_name,
    borrower_snapshots.payload, drafts.payload, gnk_certificates.file_bytes.
  - audit_log emails masked: mask_email shared helper, 3 callsites.
  - Alembic migration c5d2f3a7e1b4: schema length + data encrypt pass.
  - PII_ENC_KEYS env. Null fallback в dev. Prod startup assertion.
  - ADR-0017 + docs/operations/pii-key-rotation.md.

  ИНН + name ЮЛ + addresses + red_flags оставлены plain (публичные / search-critical).

  Closes CA-DS12.
  ```
- [ ] **Step 12.6:** push → CI watch → green.

---

## Risks / heads-up

1. **Migration атомарность:** одна транзакция, на 12+49+48+2=111 строк ≈ <1s. Если БД больше — pagination. Pre-migration `pg_dump` обязателен.
2. **Key loss = data loss:** plan'нем runbook + emphasize backup в Task 11.
3. **Legacy plain в TypeDecorator:** `gAAAAA` prefix-check — Fernet token всегда начинается с `gAAAAA` (version byte + IV base64 → детерминированный prefix). Это надёжный sentinel.
4. **JSONB legacy unwrap:** `value.get("_encrypted") is True` — без флага читаем as-is.
5. **TypeDecorator cache_ok=True:** SQLAlchemy кеширует compiled statements; cache_ok снимает warning. Поведение корректно.
6. **`get_pii_encryptor` lru_cache:** singleton на process. При rotate-deploy переменная env меняется, но контейнер restart'ится — кеш сбрасывается естественно.
7. **Tests interference:** `monkeypatch.setattr` на `config.encryption.get_pii_encryptor` — нужен `cache_clear` до и после. Pattern из T1.2.
8. **Settings prod-assert:** проверяется ТОЛЬКО `app_env in ("staging","prod")`. dev/local/test без ключа → silently NullPiiEncryptor. Это и есть fallback policy.
9. **Search ilike по ИНН/name** — не trogал, остаётся работающим (plain columns).

## Rollback

При проблемах в проде:
1. `git revert <commit>` — код вернётся к T1.2.
2. `PII_ENC_KEYS=<key>` остаётся в env — миграция downgrade decrypt'ит данные.
3. `alembic downgrade -1` через тот же ключ → plaintext restored, VARCHAR length restored.
4. Restore из pre-migration pg_dump — fallback если downgrade сломан.
