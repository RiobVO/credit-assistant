# Multi-tenant deploy playbook (T1.4 / ADR-0018)

> Approach A pure — single-tenant per deployment. Каждый банк-инстанс
> работает в собственном compose-project'е с собственными volumes,
> portами и `.env`. Изоляция гарантируется DB-level (раздельные
> Postgres-volumes), не SQL-фильтрами.

---

## Deployment model

Один банк = одна инсталляция. На одной dev-машине / staging-сервере
можно поднять несколько compose-проектов параллельно, если они
работают с разными портами, volumes и `.env` файлами.

Compose isolation primitives:
- **`--project-name <brand>`** — отдельный network namespace, контейнеры
  не видят друг друга по имени сервиса между проектами.
- **`-v <brand>_pgdata:/var/lib/postgresql/data`** — отдельный volume.
  Не существует риска cross-mount даже при ошибке оператора.
- **Offset-порты** — каждый project занимает уникальные host-ports.
- **Per-brand `.env`** — `secrets/<brand>.env`, не shared.

---

## Per-brand environment

Для каждого бренда (default, uzbekbank, hamkorbank, …) держится отдельный
`secrets/<brand>.env` с следующими переменными:

```bash
# Идентификатор brand-tenant. Обязан соответствовать `config/brands/<id>.json`.
BRAND_ID=uzbekbank

# Postgres connection — отдельный host-port для каждого инстанса.
# В compose внутри контейнера всегда `postgres:5432`.
# Host-port отличается между проектами (см. compose override).
DATABASE_URL=postgresql+asyncpg://credit:credit@postgres:5432/credit_assistant

# Redis — отдельный host-port на инстанс, container-port один и тот же.
REDIS_URL=redis://redis:6379/0

# T1.3 (ADR-0017): PII encryption ключи — отдельные на каждый банк.
# DO NOT reuse keys между банками — это нарушает confidentiality boundary.
PII_ENC_KEYS=<unique-fernet-key-per-bank>

# JWT secret — отдельный на каждый банк (refresh-token denylist в Redis
# тоже изолирован, поскольку каждый банк имеет свой Redis-контейнер).
JWT_SECRET=<unique-jwt-secret-32+bytes>

# Mode и misc.
APP_MODE=bank
APP_ENV=prod
LOG_LEVEL=INFO
CORS_ALLOWED_ORIGINS=["https://<bank-host>:3000"]
```

---

## Local dev: 2 инстанса на одной машине

Допустим, нужно проверить `default` + `uzbekbank` параллельно.

### default instance

```bash
# secrets/default.env
BRAND_ID=default
PII_ENC_KEYS=<default-key>
JWT_SECRET=<default-jwt>
APP_MODE=bank
```

```bash
docker compose --project-name credit-default \
  --env-file secrets/default.env \
  up -d
```

Host-ports от default-проекта: `5433` (Postgres), `6379` (Redis), `8000` (API).

### uzbekbank instance

`docker-compose.uzbekbank.yml` (override portов):

```yaml
services:
  postgres:
    ports:
      - "5434:5432"
  redis:
    ports:
      - "6380:6379"
  api:
    ports:
      - "8001:8000"
```

```bash
# secrets/uzbekbank.env
BRAND_ID=uzbekbank
PII_ENC_KEYS=<uzbekbank-key>
JWT_SECRET=<uzbekbank-jwt>
APP_MODE=bank
```

```bash
docker compose --project-name credit-uzbekbank \
  -f docker-compose.yml -f docker-compose.uzbekbank.yml \
  --env-file secrets/uzbekbank.env \
  up -d
```

Host-ports от uzbekbank-проекта: `5434` (Postgres), `6380` (Redis),
`8001` (API).

---

## Verification: isolation smoke

После двух запущенных проектов проверь, что данные изолированы.

### Шаг 1. Создать dossier через default-instance

```bash
curl -s -X POST http://localhost:8000/api/bank/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"t04@bank.uz","password":"T04Smoke!"}' \
  | jq -r .access_token
# скопировать ACCESS_DEFAULT

# (бизнес-API вызов на manual-input или search...)
```

### Шаг 2. Создать dossier через uzbekbank-instance

То же на `localhost:8001`. Получить ACCESS_UZBEK.

### Шаг 3. SQL-проверка изоляции

```bash
# default-instance Postgres
docker exec credit-default-postgres-1 psql -U credit -d credit_assistant \
  -c "SELECT case_id, brand_id, created_at FROM dossiers
      JOIN audit_log ON audit_log.target_id = dossiers.id
      ORDER BY dossiers.created_at DESC LIMIT 5;"

# uzbekbank-instance Postgres
docker exec credit-uzbekbank-postgres-1 psql -U credit -d credit_assistant \
  -c "SELECT case_id, brand_id, created_at FROM dossiers
      JOIN audit_log ON audit_log.target_id = dossiers.id
      ORDER BY dossiers.created_at DESC LIMIT 5;"
```

**Acceptance:** dossier'ы, созданные через `:8000`, отсутствуют в БД
uzbekbank-instance, и наоборот. `audit_log.brand_id` соответствует
своему инстансу в каждой БД.

---

## Forensics: cross-contamination detection

Single-tenant assumption нарушается, если оператор ошибочно подключит
API banc-A к БД banc-B (`DATABASE_URL` miswire). T1.4.2 защищает через
`audit_log.brand_id`:

```sql
-- Audit-log проверка раз в сутки. >1 distinct brand_id за окно — алерт.
SELECT brand_id, COUNT(*) AS events
FROM audit_log
WHERE created_at > now() - interval '24 hours'
GROUP BY brand_id;
```

Expected: одна строка с `brand_id = <current-bank>`. Две и более строк
= **cross-contamination incident**, action items:
1. Stop misconfigured API instance.
2. Audit `DATABASE_URL` / `BRAND_ID` env consistency на host.
3. Восстановить из последнего backup (`pg_dump`-based) per ADR-0014 backup policy.

Дополнительно `_validate_runtime_config` (T1.4.1) ловит mismatch
`BRAND_ID` ↔ `config/brands/<id>.json` на старте — misconfigured
deploy не запустится молча.

---

## Production checklist (новая банк-инсталляция)

1. ☐ `config/brands/<brand>.json` создан и проверен (имя банка, primary
   цвет, support контакты, business hours, optional `defaultLang`).
2. ☐ Уникальный `BRAND_ID` соответствует filename.
3. ☐ Уникальный `PII_ENC_KEYS` сгенерирован, **не reused** между банками.
4. ☐ Уникальный `JWT_SECRET` (мин. 32 байта).
5. ☐ `DATABASE_URL` указывает на dedicated Postgres-контейнер (volume
   не shared между проектами).
6. ☐ `REDIS_URL` — dedicated Redis-контейнер.
7. ☐ Alembic миграции применены: `alembic upgrade head` внутри `api`
   контейнера.
8. ☐ Seed `analysts` с MFA enforce (см. `seed_analysts` CLI).
9. ☐ Startup-log `BRAND_ID=<brand>` viewable в `docker compose logs api`
   (RuntimeError из `_validate_runtime_config` ловится здесь).
10. ☐ Forensics-query (см. выше) возвращает один `brand_id`.
11. ☐ Daily pg_dump backup configured (T3.4 — отдельная задача).

---

## Anti-patterns (don't do this)

- ❌ **Shared Postgres volume между проектами.** Volume — это границы
  isolation. Один shared volume = два процесса пишут в одну БД =
  cross-tenant data leakage гарантирована.
- ❌ **Reuse PII_ENC_KEYS между банками.** Bank-A operator с доступом
  к Bank-A key сможет расшифровать Bank-B dump.
- ❌ **One-DB-multi-tenant с brand_id WHERE filter.** PROJECT_BRIEF
  Sec 11 anti-pattern. Любая забытая `.where(brand_id=?)` = leak.
- ❌ **Manual override `BRAND_ID` на runtime через admin API.** Settings
  кэшируется на process lifetime; сменить — restart процесса с новым
  env.
