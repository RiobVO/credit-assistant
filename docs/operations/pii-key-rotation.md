# PII key rotation runbook (T1.3 / ADR-0017)

> Применяется к `PII_ENC_KEYS` env. Документирует key generation,
> rotation deploy steps, recovery from key loss.

---

## Key format

Каждый ключ — 32-byte url-safe base64 (Fernet token key).

Generate:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Example output: `iEuuP5WADM_sxwy7pgjUq6CmuiUbpDIfo-IzAg7XbpQ=`

`PII_ENC_KEYS` — comma-separated список ключей. Первый — primary (write),
остальные — read fallback для rotation.

```
PII_ENC_KEYS=KEY_NEW_BASE64,KEY_OLD_BASE64
```

---

## Initial setup (greenfield deploy)

1. Generate первичный ключ:
   ```bash
   KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
   ```
2. Сохранить ключ в **банковский Vault / KMS** (НЕ в git, НЕ на диск).
3. Прокинуть в `.env` / orchestrator secrets:
   ```
   PII_ENC_KEYS=$KEY
   ```
4. **Pre-migration backup:**
   ```bash
   docker compose exec -T postgres pg_dump -U credit credit_assistant > backup-pre-pii-$(date +%Y%m%d).sql
   ```
   Backup храним зашифрованным в off-site storage (S3 SSE / banking off-site).
5. Применить миграцию:
   ```bash
   PII_ENC_KEYS=$KEY docker compose exec -T -e PII_ENC_KEYS=$KEY api \
     uv run python -m alembic upgrade head
   ```
6. Verify: raw SELECT должен дать ciphertext с `gAAAAA` prefix.
   ```bash
   docker compose exec -T postgres psql -U credit -d credit_assistant -c \
     "SELECT substring(full_name FOR 30) FROM analysts LIMIT 1"
   ```

---

## Rotation (existing deployment)

Используется при подозрении на key compromise или плановой rotation (рекомендуется раз в год).

### Шаг 1: Generate new key

```bash
KEY_NEW=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### Шаг 2: Deploy с обоими ключами

Обновить env (Vault / orchestrator) — **new key первый**, old key вторым:

```
PII_ENC_KEYS=$KEY_NEW,$KEY_OLD
```

Restart API контейнеров. С этого момента:
- Все **новые** writes шифруются `$KEY_NEW`.
- Reads существующих row'ов (зашифрованных `$KEY_OLD`) продолжают работать через MultiFernet read-fallback.

### Шаг 3: Re-encrypt pass

Прогнать downgrade → upgrade миграцию (это decrypt'ит всё через old key, потом
re-encrypt через new):

```bash
# Backup
docker compose exec -T postgres pg_dump -U credit credit_assistant > \
  backup-pre-rotation-$(date +%Y%m%d).sql

# Downgrade (decrypt всё через old key)
docker compose exec -T -e PII_ENC_KEYS=$KEY_NEW,$KEY_OLD api \
  uv run python -m alembic downgrade -1

# Upgrade (re-encrypt всё через new key)
docker compose exec -T -e PII_ENC_KEYS=$KEY_NEW,$KEY_OLD api \
  uv run python -m alembic upgrade head
```

Альтернатива (без миграции, через app-level script): `python -m interfaces.cli.rotate_pii_keys` (если такой инструмент будет добавлен — TODO в Tier 3).

### Шаг 4: Drop old key

После успешного re-encrypt pass, обновить env — только new ключ:

```
PII_ENC_KEYS=$KEY_NEW
```

Restart API. Проверить что приложение работает: login, read dossier, generate PDF.

### Шаг 5: Secure delete old key

Old key больше не нужен; удалить из Vault / orchestrator secrets. Хранить
backup-pre-rotation в off-site storage до конца retention period (compliance —
обычно 7 лет для bank-grade).

---

## Recovery from key loss

**Если потерян active key и нет backup:**

❌ Невозможно. Encrypt'нутые данные потеряны навсегда (Fernet integrity-проверяет каждый decrypt).

**Если потерян active key но есть pre-migration `pg_dump`:**

1. Restore БД из backup:
   ```bash
   docker compose exec -T postgres psql -U credit credit_assistant < backup-pre-pii-YYYYMMDD.sql
   ```
2. Generate новый ключ, перепрогнать migration. Все PII вернутся в pre-migration состояние.

**Если потерян old key, но new key есть:**

После rotation **до завершения re-encrypt pass** — на чтение всё ещё нужен old key для row'ов, ещё не перешифрованных. Recovery:
1. Restore old key из off-site backup Vault snapshot.
2. Завершить re-encrypt pass (Шаг 3 rotation flow).

---

## Threat model out of scope

- **Compromise running process memory:** в-памяти ключ доступен root. Mitigation — банковский kernel hardening, не наш scope.
- **Side-channel attacks** (timing, power analysis): Fernet AES-128-CBC + HMAC-SHA256 не AES-GCM. Acceptable trade-off за simplicity API.
- **Quantum-resistant encryption:** не наш горизонт (pre-demo / Phase 1-3).
