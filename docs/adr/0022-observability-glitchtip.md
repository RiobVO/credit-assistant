# ADR-0022 — Observability via GlitchTip on-prem

* Status: accepted
* Date: 2026-05-18
* Tier: T3.1

## Context

После closing T3.2 (correlation_id) и T3.4 (backup/drill) появилась
последняя operational gap: error tracking. Без structured exception
reporting первый prod-инцидент в банке = «не знаем что упало, аналитик
видит 500, support вручную лезет в БД и journalctl».

Регуляторика РУз / банк compliance:
* SaaS-инструменты **запрещены** (PROJECT_BRIEF Sec 8 — «никаких внешних
  API в production»). Sentry SaaS, Bugsnag, Rollbar — исключены.
* Audit trail на инциденты должен быть **внутри банк периметра**.
* PII (ИНН, имена) **не должны** попадать в error events.

Альтернативы:

1. **Sentry SaaS** — отвергнут: data leaves периметр.
2. **Plain structured logs + SIEM** — отвергнут: банки УЗб mid-tier
   не имеют SIEM (Splunk / ELK с alerting); stacktrace grouping
   через `grep` неудобен; нет deduplication одинаковых ошибок.
3. **Highlight.io self-host** — отвергнут: не Sentry-protocol-compat,
   потребует отдельный client SDK; replay session по умолчанию
   включён, что небезопасно для banking UI.
4. **Errbit / Bugsnag self-host** — отвергнут: Errbit заброшен,
   Bugsnag self-host enterprise-only.

## Decision

**GlitchTip on-prem** + `sentry-sdk[fastapi]` (backend) + `@sentry/nextjs`
(frontend) — стандартный Sentry-protocol client'ы шлют события в
self-hosted GlitchTip Django stack.

* Backend: `init_sentry(settings)` в `create_app` ДО `configure_logging`.
  `send_default_pii=False` + custom `_before_send` scrubber. Tags:
  `brand_id`, `app_mode`, `app_env`, `request_id` (через
  RequestIDMiddleware).
* Frontend: `@sentry/nextjs` в `instrumentation.ts` (server) + `instrumentation-client.ts`
  (browser). `replaysSessionSampleRate=0` — privacy.
* Deploy: `docker-compose.observability.yml` opt-in override (4 контейнера —
  postgres + redis + web + celery worker).
* Default: `SENTRY_DSN=None` → SDK noop. Активируется через `.env` в
  staging/prod.

## Consequences

### Positive

* Industry-standard pattern: Sentry-protocol компатибельность означает
  что любой будущий client (mobile / CLI / other services) подключается
  через тот же DSN.
* PII compliance: 2 слоя защиты — `send_default_pii=False` + custom scrubber.
* Сross-correlation: events в GlitchTip ↔ structured logs через `request_id`.
* Self-hosted: data полностью в банк периметре.

### Negative

* Overhead: 4 дополнительных контейнера (postgres + redis + django + celery).
  ~500 MB RAM, ~1 GB disk для events за 30 дней.
* Django ops: банк-IT теперь поддерживает не только нашу БД, но и GlitchTip
  Django + Celery. Migrate-cycle, secret rotation, backup — отдельный stack.
* Replay session disabled: при сложных UI bugs нет visual reconstruction.
  Trade-off: privacy > debug ergonomics.
* Source-maps upload disabled: stacktraces в GlitchTip показывают minified
  filenames вместо source-line. Post-demo: настроить release pipeline
  с `sentry-cli sourcemaps upload`.

### Neutral

* Sampling: `traces_sample_rate=0`. Performance monitoring deferred — банкам
  pre-demo критичны errors, не latency percentiles (T3.3 Prometheus покрывает
  metrics).

## Implementation

См.:

* `src/infrastructure/observability/sentry.py` — backend init + scrubber.
* `web/instrumentation.ts` + `instrumentation-client.ts` — frontend hooks.
* `web/src/app/error.tsx` — App Router error boundary с `captureException`.
* `docker-compose.observability.yml` — dev sidecar override.
* `docs/operations/observability.md` — operational playbook.

## Out of scope (future ADRs)

* Performance traces / profile sampling.
* Replay session (privacy review required).
* Source-maps upload pipeline (post-demo release tooling).
* GlitchTip → email/Slack/PagerDuty alerting (configured в UI, не code).
