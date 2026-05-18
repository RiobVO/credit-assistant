# ADR-0023 — Metrics via Prometheus + Grafana

* Status: accepted
* Date: 2026-05-18
* Tier: T3.3

## Context

T3.1 (observability/GlitchTip) покрывает **errors**. Gap — performance &
business metrics: latency p99, error rate trends, PDF gen time, parser
warnings rate, rules-fired-by-severity. Без них:

* Регрессии (slow PDF, parser неудачи) обнаруживаются по жалобам, не по
  alert'ам.
* Capacity planning ("сколько borrowers/day выдержим") — guesswork.
* Compliance audit "uptime за квартал" — без quantitative back'а.

PROJECT_BRIEF Sec 3 закладывает Prometheus + Grafana как production stack
(но «не POC» — отмечает). Pre-demo это nice-to-have, но cheap чтобы
не закладывать сейчас.

Альтернативы:

1. **Plain logs + jq queries** — отвергнут: нет histogram (p99), нет
   alert-rules. Долгий debug по timestamp.
2. **InfluxDB + Telegraf** — отвергнут: heavier ops, банкам не привычен.
3. **Datadog SaaS** — отвергнут: PROJECT_BRIEF Sec 8 запрещает SaaS.
4. **OpenTelemetry + любой backend** — overengineered; Prometheus
   client достаточен.

## Decision

**Prometheus** для scrape + storage (30d retention) + **Grafana** для UI
+ dashboards. Backend через `prometheus-fastapi-instrumentator` —
de-facto standard для FastAPI: auto-instrument HTTP метрики (latency
histogram, response status counter, inflight gauge).

Custom метрики на bus business KPI:
* `pdf_render_duration_seconds` — histogram WeasyPrint generation time.
* `parser_warnings_total{format}` — counter регрессий xltx-форматов Soliq.
* `red_flags_fired_total{severity}` — counter anomaly detection.

`METRICS_ENABLED=false` default — никаких метрик/endpoint'а в dev
(zero overhead). Включается через `.env` в staging/prod.

Deploy: `docker-compose.metrics.yml` opt-in override (2 контейнера —
Prometheus + Grafana). Grafana auto-provision: datasource Prometheus +
dashboard "Credit Assistant — Operations" из bundled JSON.

## Consequences

### Positive

* Industry-standard: Prometheus + Grafana — банковский ops понимает.
* Cheap overhead: ~50 MB RAM на каждый sidecar.
* Histogram quantiles (p50/p95/p99) на client-side — точная latency
  performance picture.
* Auto-instrumentation: первый Grafana panel работает сразу после deploy
  без code changes.
* Bundled dashboard в repo — single source of truth, через git PR
  ревьюится изменение визуализации.

### Negative

* Ещё 2 контейнера в sidecar zoo (после T3.1 GlitchTip stack). Total
  observability footprint: ~6 контейнеров.
* 30d retention означает ~5 GB disk на standard prod-traffic. Tweakable
  через `--storage.tsdb.retention.time`.
* Alert rules не в коде repo — конфигурируются в Grafana UI. Trade-off:
  легче iterate, но не диффятся через git.

### Neutral

* OpenTelemetry compatibility deferred. Если когда-то перейдём на OTLP,
  Prometheus client emit-format остаётся валидным (OTel collector
  читает Prometheus endpoints).
* Single-host Prometheus — нет HA. Для bank-pilot достаточно; post-pilot
  обсудим Thanos / federated setup.

## Implementation

См.:

* `src/infrastructure/observability/metrics.py` — auto + custom metrics.
* `src/interfaces/api/app.py:create_app` — `setup_prometheus(app)` conditional.
* `docker-compose.metrics.yml` — Prometheus + Grafana sidecars.
* `deploy/metrics/prometheus/prometheus.yml` — scrape config.
* `deploy/metrics/grafana/provisioning/` — auto-provision datasource + dashboards.
* `deploy/metrics/grafana/dashboards/credit-assistant.json` — bundled dashboard.
* `docs/operations/metrics.md` — operational playbook.

## Out of scope (future ADRs)

* Alert rules как code (Prometheus AlertManager + rules files).
* Long-term storage (Thanos / Mimir).
* OpenTelemetry migration.
* SLO/error-budget tracking.
