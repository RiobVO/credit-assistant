# Observability playbook (T3.1 / ADR-0022)

> GlitchTip on-prem error tracking. Backend + frontend events через
> Sentry-protocol. PII scrubbing на 2 уровнях.

---

## 1. Что мониторится

**Errors (отправляются как Sentry events):**
* Backend: unhandled exceptions в FastAPI handler'ах (auto-instrumented
  через `FastApiIntegration`), `logger.error()` / `logger.exception()` events.
* Frontend: client-side ошибки через `error.tsx` boundary + uncaught Promise
  rejections + React render errors.
* SQL slow queries (`SqlalchemyIntegration`) — autobreadcrumb.

**Не отправляется:**
* Performance traces (`traces_sample_rate=0`).
* Profile sampling.
* DOM replay (privacy).
* Request body / cookies / Authorization headers (scrubbed).

**Tags (per-event):**
* `request_id` — correlation_id из T3.2 RequestIDMiddleware.
* `brand_id` — текущая инсталляция (T1.4).
* `app_mode` — bank/accountant.
* `app_env` — local/dev/staging/prod.

---

## 2. Dev setup

```bash
# 1. Поднимаем GlitchTip stack рядом с основной инфраструктурой:
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d

# 2. Ждём пока веб поднимется (миграции applied):
docker compose -f docker-compose.yml -f docker-compose.observability.yml \
  logs -f glitchtip-web   # Ctrl+C когда увидите "Starting development server"
```

**Создать superuser:**

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml \
  exec glitchtip-web ./manage.py createsuperuser
```

**Получить DSN:**

1. Открыть <http://localhost:8001>.
2. Sign in как superuser.
3. Settings → Projects → Create project (Platform: Python для backend,
   JavaScript/Next.js для frontend).
4. Copy DSN из project settings.

**Прокинуть DSN в credit-api:**

```bash
# В корне репо .env (или docker-compose.yml env section):
SENTRY_DSN=http://<key>@localhost:8001/<project_id>
SENTRY_ENVIRONMENT=local
# Для frontend (bundle.js видит NEXT_PUBLIC_*):
NEXT_PUBLIC_SENTRY_DSN=http://<key>@localhost:8001/<project_id>
NEXT_PUBLIC_SENTRY_ENVIRONMENT=local
```

Перезапустить `credit-api` + `npm run dev` для frontend.

**Triggering test events:**

```bash
# Backend test exception:
curl -X POST http://localhost:8000/api/bank/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "nonexistent@bank.uz", "password": "wrong"}'
# Это 401, не event. Для test event — временно бросить exception в handler.

# Frontend — открыть /search, в DevTools console:
# Sentry.captureException(new Error("test from devtools"))
```

GlitchTip UI обновится в течение 5-10 секунд (Celery worker обрабатывает).

---

## 3. PII review

`_before_send` filter в `src/infrastructure/observability/sentry.py`:

* **Drops** `request.data`, `request.cookies` (могут содержать password / JWT).
* **Scrubs keys** matching `password|token|secret|api[_-]?key|authorization|cookie|mfa|backup_codes|pii_enc|jwt` → `[scrubbed]`.
* **Masks emails** в breadcrumbs / extra / tags / headers (через
  `infrastructure.auth.email_mask.mask_email`).

Что **может** попасть в events (verify в GlitchTip UI):
* Stacktrace (источник, без переменных, по умолчанию).
* Exception message — может содержать ИНН если код его форматит. **Не делать
  `raise ValueError(f"bad inn: {inn}")`** — лучше `logger.error("bad_inn",
  inn_masked=mask_inn(inn))`.
* SQL query (без bind-params) от `SqlalchemyIntegration`.

---

## 4. Production deploy

### Option A — bundled с основным stack

GlitchTip живёт в той же docker-compose стэк как и `credit-api`, на
отдельном subdomain (Caddy proxy).

`Caddyfile.template`:

```
glitchtip.{$CADDY_DOMAIN} {
  reverse_proxy glitchtip-web:8000
  header {
    X-Frame-Options "DENY"
  }
}
```

Plus: `connect-src` для frontend Sentry SDK:

```
{$CADDY_DOMAIN} {
  ...
  header Content-Security-Policy "connect-src 'self' https://glitchtip.{$CADDY_DOMAIN}"
}
```

### Option B — отдельный host

GlitchTip — отдельная инсталляция на dedicated VM. Backend и frontend
шлют события через VPN/firewall-allowed route. См. <https://glitchtip.com/documentation>.

### Backup

GlitchTip Postgres backup настраивается так же как credit-postgres (T3.4):
sidecar `pg_dump` на cron, retention 30d. Отдельный age recipient если
шифруем (events содержат stacktraces — sensitive).

---

## 5. Alert rules

GlitchTip UI → Settings → Alerts:

| Trigger | Action | Severity |
|---|---|---|
| New issue type (first seen) | Email + Slack webhook | medium |
| Issue rate >10/hour | Email | high |
| Critical-level event | Email immediate | critical |
| Issue regression (resolved → seen again) | Email | medium |

Email прокидывается через `EMAIL_URL` env GlitchTip (SMTP).

---

## 6. Cross-reference event ↔ structured log

При расследовании инцидента:

1. GlitchTip event → копировать `request_id` из tag-секции.
2. На host: `journalctl -u credit-assistant | grep <request_id>` — даст
   весь сюжет (login → search → exception → 500).
3. `SELECT * FROM audit_log WHERE request_id = '<request_id>'` — действия
   пользователя.
4. Stacktrace в event → строка кода → диагноз.

---

## 7. Troubleshooting

### Events не приходят в GlitchTip

1. Проверить `SENTRY_DSN` env активна в credit-api:
   ```bash
   docker compose exec api bash -c 'echo $SENTRY_DSN'
   ```
2. Глянуть логи sentry в api:
   ```bash
   docker compose logs api | grep -i sentry
   ```
3. Sentry SDK debug:
   ```python
   sentry_sdk.init(dsn=..., debug=True)  # печатает что отправляется
   ```
4. Network: из credit-api контейнера curl до GlitchTip:
   ```bash
   docker compose exec api curl -v http://glitchtip-web:8000/api/0/store/
   ```

### DSN отвергается с 401

Project key mismatch. Re-copy DSN из GlitchTip UI → project settings.

### Events приходят но без request_id tag

Middleware order issue. `init_sentry` должен быть **до** `configure_logging`
в `create_app`. RequestIDMiddleware должен быть **последним** `add_middleware`
(outer в LIFO стеке) — чтобы Sentry scope tag set перед handler'ом.

### Stacktrace показывает minified filenames

Sourcemaps не uploaded (default). Это known limitation pre-demo. Post-demo:
настроить `sentry-cli sourcemaps upload` в CI release pipeline.

### PII попала в event

Если в GlitchTip event видишь ИНН/email в exception message:
1. **Не игнорировать** — это compliance breach.
2. Найти call-site (вероятно `raise ValueError(f"...{inn}...")`).
3. Заменить на `logger.error("descriptive_event", masked_inn=mask_inn(inn))`
   + `raise <SafeException>` без plain PII.
4. Удалить инцидентный event из GlitchTip (Settings → Events → Delete).

---

## 8. Operational checklist

**Daily:**
* [ ] GlitchTip UI → check new issues. Triage по severity.
* [ ] Verify event ingestion rate (UI → Stats).

**Weekly:**
* [ ] Resolve / mark as ignored stale issues (>7d без re-occurrence).
* [ ] Review alert email volume — adjust thresholds если шумно.

**Monthly:**
* [ ] GlitchTip Postgres backup verified (см. T3.4 backup playbook).
* [ ] PII scrubbing review — sample 10 random events на наличие unmasked PII.

**Quarterly:**
* [ ] GlitchTip version upgrade.
* [ ] Sentry SDK upgrade.
* [ ] DSN rotation (revoke old, issue new).

---

## 9. References

* ADR-0022 — Observability decision rationale.
* `src/infrastructure/observability/sentry.py` — backend init.
* `web/instrumentation.ts` + `web/instrumentation-client.ts` — frontend.
* `web/src/app/error.tsx` — App Router error boundary.
* `docker-compose.observability.yml` — GlitchTip sidecar override.
* GlitchTip docs: <https://glitchtip.com/documentation>
* Sentry SDK Python: <https://docs.sentry.io/platforms/python/>
* Sentry SDK Next.js: <https://docs.sentry.io/platforms/javascript/guides/nextjs/>
