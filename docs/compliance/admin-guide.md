# Admin Guide

> Руководство администратора Credit Assistant MSB. Аудитория — DevOps / SRE
> банка-клиента, отвечающие за on-premise эксплуатацию.
>
> **Документ — draft skeleton (T4 compliance pack).** Версия 0.1, требует
> финальной редактуры перед передачей в банк.

---

## Russian

### 1. Системные требования

**Минимальная конфигурация (single-tenant, до 200 заёмщиков/день):**

- CPU: 4 vCPU (x86-64)
- RAM: 8 GiB
- Disk: 100 GiB SSD (БД + PDF/backup retention 90 дней)
- OS: Linux x86-64 с поддержкой Docker 24+ (Ubuntu 22.04 LTS / RHEL 9 / Debian 12)
- Сеть: исходящие 443 для CBU API (опционально, on-prem mode допускает offline)

**Рекомендуемая конфигурация (multi-tenant, до 1000 заёмщиков/день):**

- CPU: 8 vCPU
- RAM: 16 GiB
- Disk: 500 GiB SSD + отдельный том для backup

**Сетевые порты:**

| Порт | Назначение | Доступ |
|------|------------|--------|
| 443  | HTTPS (Caddy) | внешний (банковская сеть) |
| 80   | HTTP redirect → 443 | внешний |
| 8000 | FastAPI (внутренний) | localhost only |
| 5432/5433 | Postgres | localhost only |
| 6379 | Redis | localhost only |
| 3000 | Next.js dev | dev only, в проде закрыт |

### 2. Установка и развёртывание

**Tarball-инсталляция.** Полная процедура — `deploy/README.md`. Краткий
сценарий:

```bash
tar -xzf credit-assistant-<version>.tar.gz
cd credit-assistant
cp .env.example .env  # отредактировать критичные секреты
./deploy/install.sh
docker compose up -d
```

**Multi-tenant deploy** (отдельный compose-project на каждый банк) —
`docs/operations/multi-tenant-deploy.md` + ADR-0018.

### 3. Конфигурация

**Критичные environment variables (`.env`):**

| Variable | Назначение | Обязательно |
|----------|------------|-------------|
| `APP_MODE` | `bank` или `accountant` | да |
| `BRAND_ID` | резолвится в `config/brands/<id>.json` | да |
| `JWT_SECRET` | подпись JWT, мин. 32 байта | да (prod) |
| `PII_ENC_KEYS` | comma-separated Fernet keys | да (prod) |
| `REDIS_URL` | `redis://redis:6379/0`, иначе stateless fallback | рекомендуется |
| `AUTHN_MODE` | `seeded` или `ldap` (default `seeded`) | нет |
| `LDAP_*` | bind DN, password, search filter (при `AUTHN_MODE=ldap`) | условно |
| `DATABASE_URL` | Postgres DSN | да |
| `CBU_API_URL` | для курсов валют (опционально) | нет |

**Brand-config:** `config/brands/<id>.json` — JSON со scheme'ом
`BrandConfig` (имя банка, логотип, `defaultLang`, `support`, `businessHours`).

### 4. Backup и восстановление

Полная процедура — `docs/operations/db-backup.md`.

- **Backup sidecar `credit-db-backup`** — ежедневный `pg_dump` в `./backups/`
  (gitignored).
- **Retention:** 30 дней по умолчанию, конфигурируется через
  `BACKUP_RETENTION_DAYS`.
- **Restore drill:** `./deploy/restore-drill.sh <backup-file>` — поднимает
  shadow-инстанс, проверяет integrity, exit 0 при PASS.
- **Off-site copy:** банк отвечает за репликацию `./backups/` на внешний
  storage (рекомендация — rsync с шифрованным каналом).

### 5. PII encryption и ротация ключей

Полная процедура — `docs/operations/pii-key-rotation.md` + ADR-0017.

**Краткое:**

- `PII_ENC_KEYS` — comma-separated Fernet keys. Первый — primary write,
  остальные — read fallback (для grace-period ротации).
- 6 зашифрованных колонок: `analysts.full_name`, `analysts.mfa_secret`,
  `borrowers.director_name`, `borrower_snapshots.payload`, `drafts.payload`,
  `gnk_certificates.file_bytes`.
- **Ротация (high-level):**
  1. Сгенерировать новый ключ (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
  2. Добавить новый ключ **перед** старым в `PII_ENC_KEYS`.
  3. Restart API, дождаться re-encryption фонового job'а.
  4. Удалить старый ключ из `PII_ENC_KEYS` после verification.

### 6. LDAP / authentication

Полная процедура — `docs/operations/ldap-setup.md` + ADR-0019.

**Краткое:**

- `AUTHN_MODE=ldap` активирует `LdapAuthnAdapter`.
- Service-bind (`LDAP_BIND_DN`, `LDAP_BIND_PASSWORD`) → search
  (`LDAP_USER_SEARCH_FILTER`) → user-bind для проверки пароля.
- Roles резолвятся по `memberOf` (senior precedence над analyst).
- **Lazy upsert** — при первом login создаётся row в `analysts` с
  `password_hash=NULL`, `authn_source='ldap'`.

**Break-glass procedure:**

- Whitelist email в `ADMIN_BREAK_GLASS_EMAILS` — обходит LDAP, использует
  seeded credentials.
- Используется при отказе AD/LDAP (cuanto только админам безопасности).

### 7. Мониторинг и observability

- **GlitchTip (Sentry-compatible)** — error tracking. Полная конфигурация
  `docs/operations/observability.md` + ADR-0022.
  - Что смотреть: unhandled exceptions, slow transactions, performance issues.
  - URL: `<glitchtip-host>/projects/credit-assistant/issues/`.
- **Prometheus + Grafana** — metrics. Полная конфигурация
  `docs/operations/metrics.md` + ADR-0023.
  - Что смотреть: request rate, latency p50/p95/p99, error rate, БД health,
    Redis health.
  - Dashboards: `<grafana-host>/d/credit-api-overview/`.

**Alerting:** правила через Grafana UI (пока не rules-as-code). Критичные:
- API down >2 min
- БД connection pool exhausted
- Redis down (degraded refresh-token rotation)
- Error rate >5% за 5 min

### 8. Логирование

- **Формат:** structlog JSON, stdout контейнера.
- **Correlation ID:** `correlation_id` пробрасывается через все слои
  (HTTP middleware → logger context → DB queries при diagnostic mode).
- **PII filtering:** ИНН маскируется (`XXXXXX1234`), email маскируется
  (`u***@bank.uz`), full_name не логируется никогда.
- **Сбор:** `docker compose logs api` + рекомендуется отправка в
  банковский SIEM (syslog forwarder или fluentd).
- **Ротация:** Docker log driver `json-file` с `max-size=100m, max-file=5`
  по умолчанию.

### 9. User management

**Seed analyst (initial setup):**

```bash
docker compose exec api bash -c "cd /app/src && uv run --no-sync python -m interfaces.cli.seed_analysts --email <email> --password <password> --full-name '<name>'"
```

**MFA reset (analyst забыл TOTP):**

```bash
docker compose exec api bash -c "cd /app/src && uv run --no-sync python -m interfaces.cli.reset_mfa --email <email>"
```

Аналитик при следующем login пройдёт MFA enrollment заново.

**Role assignment:**

- В `seeded` режиме — поле `role` в `analysts` (`analyst` / `senior`).
- В `ldap` режиме — resolved из `memberOf` групп, см. ADR-0019.

### 10. Эскалация инцидентов

**Контакт-матрица (placeholder, требует заполнения банком):**

| Уровень | Роль | Контакт | SLA ответа |
|---------|------|---------|------------|
| L1 | DevOps дежурный | TBD | 15 мин (24/7) |
| L2 | Tech Lead | TBD | 1 час (business hours) |
| L3 | Vendor escalation | TBD | 4 часа |

**Типы инцидентов и эскалация:**

- API down → L1 → L2 при non-recovery >15 min.
- БД data loss → L1 + L3 (vendor) немедленно.
- PII breach подозрение → L1 + L3 + Security Officer банка (legal escalation
  per Закон РУз №547).

---

## O'zbek

> Eslatma: ushbu bo'lim mashinaviy tarjima asosida tayyorlangan skelet.
> Har bir bo'limga `TODO[CA-T4-UZ]` belgisi qo'yilgan — yakuniy tahrir
> uchun o'zbek mutaxassisi kerak.

### 1. Tizim talablari

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

Minimal konfiguratsiya (kuniga 200 qarz oluvchigacha): 4 vCPU, 8 GiB RAM,
100 GiB SSD, Linux x86-64 Docker 24+ qo'llab-quvvatlashi bilan.

### 2. O'rnatish va joylashtirish

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

Tarball-o'rnatish — `deploy/README.md` ko'ring. Multi-tenant joylashtirish —
`docs/operations/multi-tenant-deploy.md` + ADR-0018.

### 3. Konfiguratsiya

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

Kritik environment variables: `APP_MODE`, `BRAND_ID`, `JWT_SECRET`,
`PII_ENC_KEYS`, `REDIS_URL`, `AUTHN_MODE`, `DATABASE_URL`.

### 4. Zaxira nusxa va tiklash

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

To'liq protsedura — `docs/operations/db-backup.md`. Kunlik `pg_dump` sidecar
`credit-db-backup` orqali, 30 kun retention.

### 5. PII shifrlash va kalit aylanishi

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

To'liq protsedura — `docs/operations/pii-key-rotation.md` + ADR-0017.
Fernet/MultiFernet, 6 ta shifrlangan ustun.

### 6. LDAP / autentifikatsiya

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

To'liq protsedura — `docs/operations/ldap-setup.md` + ADR-0019. Break-glass
ro'yxati `ADMIN_BREAK_GLASS_EMAILS` env orqali.

### 7. Monitoring va kuzatuv

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

GlitchTip — `docs/operations/observability.md` + ADR-0022. Prometheus +
Grafana — `docs/operations/metrics.md` + ADR-0023.

### 8. Loglar

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

structlog JSON formati, `correlation_id` barcha qatlamlar bo'ylab.
PII filtrlash: STIR maskalanadi (`XXXXXX1234`).

### 9. Foydalanuvchilarni boshqarish

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

Seed analyst CLI, MFA reset CLI — yuqoridagi RU bo'limidagi buyruqlar.

### 10. Hodisalarni eskalatsiya qilish

`TODO[CA-T4-UZ]: trebuetsya ruchnaya redaktura uzbekskogo eksperta`

L1/L2/L3 kontakt matritsasi — bank tomonidan to'ldirilishi kerak.
PII breach holatida — №547-sonli Qonun bo'yicha huquqiy eskalatsiya.
