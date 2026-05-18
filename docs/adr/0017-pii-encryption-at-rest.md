# ADR-0017 — PII encryption at rest (column-level через app-layer)

**Status:** Accepted · **Date:** 2026-05-18 · **Context:** T1.3 (Pre-Demo Roadmap), closes CA-DS12

## Context

Bank-grade compliance (Закон РУз №547 «О персональных данных», internal-security audit) требует, чтобы PII не покидал периметр банка в виде plain-text. Threat-model для нашего внутреннего инструмента — stolen DB dump или backup-leak: атакующий получает `pg_dump` файл или snapshot диска и читает всё подряд.

Pre-T1.3 состояние:
- `analysts.full_name` — PII банковского сотрудника, plain VARCHAR(255).
- `analysts.mfa_secret` — TOTP shared secret, plain (TODO[CA-DS12]).
- `borrowers.director_name` — PII физлица, plain.
- `borrower_snapshots.payload` — JSONB со всем снимком, включая контрагентов и evidence.
- `drafts.payload` — JSONB manual-input, TTL 30d, может содержать PII.
- `gnk_certificates.file_bytes` — PDF blob справки ГНК, может содержать director identity.
- `audit_log.payload` — JSONB, в 2 callsite'ах хранил full email plaintext.

Не PII (оставляем plain):
- ИНН ЮЛ — публичный в реестре `soliq.uz/services/search/`.
- Название ЮЛ, юр.адрес, ОКВЭД — публичные.
- `analysts.email` — login identifier, нужен для уникального lookup; employees of the same bank know each other's emails.
- `dossiers.red_flags` JSONB — рендерится на каждый list-view UI, цена decrypt на N записей не оправдана.
- `dossiers.severity_breakdown` — агрегатные счётчики.
- `usd_uzs_rates`, `system_uptime_day` — не PII.

## Decision

**Column-level app-layer encryption** через SQLAlchemy `TypeDecorator` + `cryptography.Fernet` / `MultiFernet`. **6 PII-колонок** шифруются:

| Column | TypeDecorator | Rationale |
|---|---|---|
| `analysts.full_name` | `EncryptedString(500)` | PII сотрудника |
| `analysts.mfa_secret` | `EncryptedString(200)` | Crypto material (closes CA-DS12) |
| `borrowers.director_name` | `EncryptedString(500)` | PII физлица |
| `borrower_snapshots.payload` | `EncryptedJsonb` (wrap pattern) | Dense PII |
| `drafts.payload` | `EncryptedJsonb` (wrap pattern) | Manual input PII |
| `gnk_certificates.file_bytes` | `EncryptedBytea` | PDF с PII inside |

Plus: `audit_log.payload` — **mask** через shared `infrastructure/auth/email_mask.py` (cheaper, audit ещё debuggable). 3 callsites: `mfa.py`, `authenticate_analyst.py`, `admin.py`.

### Key management

- `PII_ENC_KEYS` env: comma-separated Fernet keys (32-byte url-safe base64). Первый — primary (write), остальные — read fallback для rotation.
- `MultiFernet([new, old])` — encrypt всегда первым ключом; decrypt пробует все по порядку.
- Rotation runbook: `docs/operations/pii-key-rotation.md`.

### Fallback policy

- `PII_ENC_KEYS=` пустая → `NullPiiEncryptor` passthrough. Сохраняет dev/test/local поведение, миграция без ключа выполняет только schema-changes.
- Production startup-assertion в `interfaces/api/app.py`: `if app_env in ("staging","prod") and not pii_enc_keys: raise RuntimeError`. Misconfigured prod не запустится молча.

### Backward-compat read

TypeDecorator используют sentinel для прозрачного чтения legacy plaintext (до миграции / при downgrade):
- `EncryptedString` — Fernet token всегда начинается с `gAAAAA` (version byte + IV base64). Без префикса → возвращаем plain as-is.
- `EncryptedBytea` — то же на `b"gAAAAA"`.
- `EncryptedJsonb` — wrap pattern `{"_encrypted": true, "ciphertext": "..."}`. Без флага → возвращаем dict as-is.

Это нужно чтобы:
- Pre-migration data была доступна сразу после rollout кода (без принудительного migration order).
- Rollback без ключа не валил приложение (data остаётся encrypt'нутой, но приложение читает её через legacy-branch — пустота вместо crash).

### Migration policy

Alembic `c5d2f3a7e1b4` (`20260518_2000_pii_encryption.py`):
1. ALTER COLUMN length expansions (3 TEXT-колонки).
2. Data encrypt pass — SELECT plain → encrypt в Python → UPDATE. Idempotent: rows с `gAAAAA` или `_encrypted: true` skip'аются.
3. Без `PII_ENC_KEYS` env — schema-only (length), data plain (приложение читает через legacy-branch).

**Pre-migration `pg_dump` обязателен**. Потеря ключа = data loss. Backup восстанавливает plain pre-T1.3 состояние.

## Alternatives considered

- **pgcrypto / transparent disk encryption** (LUKS, AWS KMS): защита от physical disk access, но pg_dump текст-репликация всё равно содержит plaintext. Дополняет, не заменяет app-layer.
- **Blind-index для INN (`HMAC-SHA256(inn, pepper)`)**: позволил бы шифровать ИНН + сохранить ilike-search через hash-equality. Rejected — ИНН в УЗ публичный, дополнительная column + миграция + 2 update-сайта search не оправданы.
- **Full row encryption** (encrypt всё JSONB заранее, decrypt на каждом read): дороже на read-time, ломает индексы / partial JSONB queries. Только snapshot/draft/red_flags могут — но `red_flags` нужен в list view UI.
- **Hashicorp Vault / cloud KMS**: deferred — банковский on-prem может не иметь Vault. Env-key достаточен для POC и первого пилота; runbook описывает переход на Vault в production.
- **Single Fernet ключ без rotation**: проще, но без rotation runbook ключ-loss требует pg_dump restore. MultiFernet даёт graceful rotation без downtime.

## Trade-offs

- **Key loss = data loss.** Pre-migration pg_dump backup mandatory.
- **Fernet token width:** 255 plaintext → ~432 base64 chars. Column length expanded × ~2 для строковых полей.
- **Read perf:** ~50µs decrypt на snapshot ~10KB. Acceptable для PDF render / dossier API (single record).
- **JSONB query внутрь payload недоступен** (encrypt'нуто как opaque blob). Не used сейчас (rules engine читает целиком, search идёт через `borrowers`).
- **Migration в одной транзакции** на 111 строк (12 borrowers + 49 snapshots + 48 drafts + 2 analysts) ≈ <1s. На больших prod-БД (тысячи строк) — pagination.
- **Tests** монopolизируют `get_pii_encryptor` singleton; cache_clear() обязателен после monkeypatch.

## Implementation

**Файлы:**
- `src/application/ports/pii_encryptor_port.py` — `PiiEncryptorPort` Protocol.
- `src/infrastructure/encryption/{null,fernet}_pii_encryptor.py` — два адаптера.
- `src/infrastructure/persistence/types/encrypted_{string,jsonb,bytea}.py` — TypeDecorator'ы.
- `src/config/encryption.py` — `get_pii_encryptor()` singleton factory.
- `src/infrastructure/persistence/models/{analyst,borrower,borrower_snapshot,draft,gnk_certificate}.py` — 6 column swaps.
- `src/infrastructure/auth/email_mask.py` — shared mask helper (3 callsites: mfa, authenticate_analyst, admin).
- `src/infrastructure/persistence/migrations/versions/20260518_2000_pii_encryption.py` — Alembic.
- `src/interfaces/api/app.py` — production startup assertion.
- `docs/operations/pii-key-rotation.md` — runbook (key generation, rotation steps, recovery).

**Tests:** 5 unit (Null) + 8 unit (Fernet с rotation/invalid) + 9 unit (TypeDecorator) + 5 unit (mask_email) + 6 integration (testcontainers raw SELECT vs ORM SELECT).

## Security checklist

- [x] Plaintext в БД отсутствует после миграции (raw SELECT даёт ciphertext с `gAAAAA` prefix).
- [x] Key not in code/git: `.env.example` пустое, `.gitignore` покрывает `.env`.
- [x] Production без `PII_ENC_KEYS` не запускается (RuntimeError on boot).
- [x] Rotation runbook документирует key generation, deploy steps, re-encrypt pass.
- [x] Pre-migration backup mandatory (документировано в runbook).
- [x] Audit log emails masked (no full PII leak).
- [x] Fernet token integrity check встроен (HMAC inside) — corrupt token → InvalidPiiTokenError.
- [ ] Vault / HSM integration — deferred to production deploy phase.
- [ ] Key rotation процедура отрепетирована в staging — deferred (нет staging пока).

## Acceptance

- 6 PII columns в БД содержат ciphertext (raw SQL).
- ORM SELECT через TypeDecorator транспарентно decrypt'ит (verified `pii_encryption_roundtrip_test.py`).
- `bank_auth_test`, `borrower_repository_test`, `gnk_certificate_repository_test`, etc. продолжают работать (NullPiiEncryptor fallback или MonkeyPatch).
- Production startup-assert ловит misconfigured prod (env `app_env=prod`, нет `PII_ENC_KEYS`).
- Audit log в `bank_auth_test` / `bank_admin_test` — email = `iv***@bank.uz` masked.
