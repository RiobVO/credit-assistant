# T3.1 — Observability (error tracking) via GlitchTip on-prem

> Backend + frontend error tracking. SaaS Sentry **запрещён** (PROJECT_BRIEF
> Sec 8 — data leaves периметр банка). GlitchTip — OSS Sentry-compatible,
> self-host. Использует T3.2 correlation_id для tags.

## Decisions (defaults)

- Backend: `sentry-sdk[fastapi]` — FastAPI integration auto-instruments
  request/response, SqlAlchemy integration логирует slow queries.
- Frontend: `@sentry/nextjs` — server + browser runtime, instrumentation.ts hook.
- GlitchTip dev sidecar — opt-in через `docker-compose.observability.yml`
  (4 контейнера django + postgres + redis + worker — heavy).
- `send_default_pii=False` + custom `before_send` scrubber для double-safety.
- Sampling: 100% errors, 0% traces (банкам traces не критично).
- `SENTRY_DSN=None` → SDK noop. Default off, opt-in через .env.
- Tags: `request_id` (T3.2), `brand_id` (T1.4), `authn_source` (T1.5),
  `app_mode` (bank/accountant), `app_env` (local/dev/staging/prod).

## Out of scope

- Performance monitoring / traces — sample rate 0 в default.
- Profile sampling — overhead для bank-internal scale.
- Source-map upload в GlitchTip — нужен для prod, но требует release-pipeline
  (post-demo).
- Replay session — приватность banking UI, оставлено disabled.

## Atomic split

### T3.1.1 — Backend sentry-sdk init + tags integration

**Файлы:**
1. `pyproject.toml` — добавить `sentry-sdk[fastapi]>=2.20` в `dependencies`.
2. `src/config/settings.py` — `sentry_dsn: str | None`, `sentry_environment:
   str = "local"`, `sentry_release: str | None`.
3. `src/infrastructure/observability/__init__.py` (новый).
4. `src/infrastructure/observability/sentry.py` (новый):
   - `init_sentry(settings)` — `sentry_sdk.init(dsn, environment, release,
     send_default_pii=False, traces_sample_rate=0, before_send=_scrub,
     integrations=[FastApiIntegration(), SqlalchemyIntegration(), LoggingIntegration(...)])`.
   - `_scrub(event, hint)` — drop request.body / request.cookies / extra
     containing 'email|inn|password|token|secret'. Email маскируется через
     `infrastructure.auth.email_mask.mask_email`.
   - `init_sentry(None)` → noop.
5. `src/interfaces/api/app.py` — `init_sentry(settings)` **перед**
   `configure_logging` (sentry интегрирует logging-handler).
6. `src/interfaces/api/middleware.py` — `RequestIDMiddleware.dispatch`
   дополнительно: `sentry_sdk.get_current_scope().set_tag("request_id", rid)`.
   Также `set_tag("brand_id", settings.brand_id)` через DI hook.
7. `src/infrastructure/observability/sentry_test.py` (новый) — unit:
   - `test_init_sentry_with_none_dsn_is_noop` — assert hub.client is None.
   - `test_scrub_drops_request_body` — fake event с body → cleared.
   - `test_scrub_masks_email_in_breadcrumbs` — email → masked.
   - `test_init_sets_environment_and_release_tags` — captured event имеет tags.
8. `src/interfaces/api/middleware_test.py` — extend: assert `set_tag` вызывается
   с request_id (mock `sentry_sdk.get_current_scope`).

**TDD:**
- Red 1: scrub test без implementation → ImportError.
- Green 1: minimal `init_sentry` + `_scrub`.
- Red 2: middleware tag test без scope.set_tag → fail.
- Green 2: добавить tag injection.

**Verify:** ruff + mypy strict + pytest unit на sentry_test.

**Commit:** `feat(observability): T3.1.1 sentry-sdk init + PII scrubber + request_id tag`.

---

### T3.1.2 — Frontend @sentry/nextjs + error.tsx rewrite

**Файлы:**
1. `web/package.json` — `@sentry/nextjs` в deps.
2. `web/instrumentation.ts` (новый) — server runtime Sentry init (читает
   `SENTRY_DSN` env, environment, release).
3. `web/instrumentation-client.ts` (новый) — browser-side Sentry init
   (`NEXT_PUBLIC_SENTRY_DSN` env). `replaysSessionSampleRate: 0` —
   приватность.
4. `web/next.config.ts` — `withSentryConfig` wrap. `silent: true` для clean
   build. **Disable source-maps upload** (`disableServerWebpackPlugin: true`
   + `disableClientWebpackPlugin: true` — sourcemaps generated локально,
   не uploaded). В prod-build pipeline это переключается на opt-in.
5. `web/src/app/error.tsx` — заменить `console.error` + `TODO[CA-064]` на
   `Sentry.captureException(error, { tags: { digest: error.digest } })`.
6. `web/src/app/global-error.tsx` (новый) — App Router top-level error boundary
   для глобальных rendering ошибок (отдельно от error.tsx, который ловит
   route-level).
7. `web/tests/sentry-error-boundary.test.tsx` (новый) — RTL: error → Sentry
   mock получает captureException.

**TDD:** vitest mock `@sentry/nextjs.captureException` → fire error → assert called.

**Verify:** `npm run build` + `npm run test:run`.

**Commit:** `feat(web): T3.1.2 @sentry/nextjs integration + error boundary`.

---

### T3.1.3 — GlitchTip dev sidecar + ADR-0022 + playbook

**Файлы:**
1. `docker-compose.observability.yml` (override) — services:
   - `glitchtip-postgres` (postgres:16-alpine, отдельный db).
   - `glitchtip-redis` (redis:7-alpine).
   - `glitchtip-web` (`glitchtip/glitchtip:latest`) — Django web на :8001.
   - `glitchtip-worker` (тот же image) — Celery beat + worker.
   - env: `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `DEFAULT_FROM_EMAIL`.
   - Mount volumes для postgres + worker uploads.
2. `docs/adr/0022-observability-glitchtip.md`:
   - Context: PROJECT_BRIEF Sec 8 запрещает SaaS (data outside банк периметр).
   - Alternatives: Sentry SaaS (rejected — compliance), plain logs + SIEM
     (rejected — нет stacktrace + grouping), Highlight.io self-host (rejected —
     не Sentry-compat protocol).
   - Decision: GlitchTip on-prem + sentry-sdk client'ы.
   - Trade-offs: 4 контейнера на сервере / +500 MB RAM / Django/Celery deps.
3. `docs/operations/observability.md`:
   - Section 1: что мониторится (errors + structured logs cross-ref).
   - Section 2: dev setup (`docker compose -f docker-compose.yml -f
     docker-compose.observability.yml up -d`).
   - Section 3: GlitchTip project setup (create org, get DSN, .env wiring).
   - Section 4: alert rules (email/webhook на critical errors).
   - Section 5: production deploy (либо в compose stack, либо отдельный host).
   - Section 6: PII обзор — что scrub'ается, что попадает в events.
   - Section 7: troubleshooting (DSN не работает / events не приходят /
     correlation_id потерян).
4. `deploy/.env.example` — добавить `SENTRY_DSN=` (commented, opt-in).
5. `deploy/Caddyfile.template` — комментарий о `connect-src` для GlitchTip
   (если frontend Sentry SDK шлёт прямо в GlitchTip, CSP должен пропустить).

**Verify:** `docker compose -f docker-compose.yml -f
docker-compose.observability.yml config` syntax check.

**Commit:** `docs(arch): T3.1.3 ADR-0022 + GlitchTip sidecar + observability playbook`.

---

### T3.1.4 — Docs sync

**Файлы:** CLAUDE.md + `docs/pre-demo-roadmap.md`.

**Commit:** `docs(internal): T3.1 observability closure + Tier 3 progress`.

---

## Verify (full)

После каждого atomic commit:
```bash
PYTHONPATH=src uv run --no-sync python -m ruff check . && \
  uv run --no-sync python -m mypy --strict src/ tests/ && \
  uv run --no-sync python -m pytest -q
```

Frontend:
```bash
cd web && npm run lint && npm run test:run && npm run build
```

CI прогонит integration через testcontainers (ubuntu-latest имеет Docker
preinstalled — backup/drill PASS, тот же путь для T3.1).

## Estimate

- T3.1.1 backend — 2.5h
- T3.1.2 frontend — 2h
- T3.1.3 sidecar + ADR + playbook — 2.5h
- T3.1.4 docs — 0.5h

**Total: ~7.5h.**

## Risks / open subtleties

- `LoggingIntegration` от sentry-sdk автоматически перехватывает stdlib logs.
  Может конфликтовать с моим `setLogRecordFactory` из T3.2. Проверить —
  factory срабатывает на `LogRecord.__init__`, Sentry integration на
  `Handler.emit`. Должно совмещаться (factory сначала, handler потом видит
  enriched record).
- `init_sentry` до `configure_logging`: sentry устанавливает свой stdlib
  `LoggingIntegration` через `breadcrumb_handler` + `event_handler` — это
  ADDS handlers, не replaces. Idempotency мой `_CONFIGURED` flag не пострадает.
- Frontend `withSentryConfig` совместим с `output: "standalone"`: проверить
  на `npm run build`. Если не работает — отключить source-maps upload через
  config options.
- GlitchTip Django: при первом старте требует migrate. Healthcheck должен
  ждать миграций. В docker-compose.observability.yml — `migrate` command
  как init job.
- `replaysSessionSampleRate: 0`: критично для banking UI privacy. Никогда
  не записывать DOM mutations.
