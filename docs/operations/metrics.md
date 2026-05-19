# Metrics playbook (T3.3 / ADR-0023)

> Prometheus scrape + Grafana dashboard pack для Credit Assistant.
> Auto-instrumentation HTTP + 3 custom метрики на бизнес-KPI.

---

## 1. Что собирается

**Auto через `prometheus-fastapi-instrumentator`:**

| Metric | Тип | Labels | Семантика |
|---|---|---|---|
| `http_requests_total` | counter | method / handler / status_code | request rate, error rate |
| `http_request_duration_seconds` | histogram | method / handler / status_code | latency p50/p95/p99 |
| `http_inprogress_requests` | gauge | — | inflight concurrency |

**Custom (`infrastructure/observability/metrics.py`):**

| Metric | Тип | Labels | Что мониторим |
|---|---|---|---|
| `pdf_render_duration_seconds` | histogram | — | WeasyPrint регрессии |
| `parser_warnings_total` | counter | `format` (vat_declaration/vat_registry_ilova/form_1/form_2/profit_tax) | регрессии xltx форматов Soliq |
| `red_flags_fired_total` | counter | `severity` (critical/high/medium/low) | anomaly detection через всплески critical |

**Не собирается:**

* Performance traces / spans — heavy + дублирует GlitchTip (T3.1).
* SQL query metrics — `SqlalchemyIntegration` GlitchTip уже шлёт slow queries.
* Process / system metrics (CPU, memory, disk) — банк-IT стандартно мониторит
  через node_exporter; добавим только если попросят.

---

## 2. Dev setup

```bash
# 1. Включить /metrics endpoint в credit-api:
echo "METRICS_ENABLED=true" >> .env
docker compose up -d --build api

# 2. Поднять Prometheus + Grafana sidecars:
docker compose -f docker-compose.yml -f docker-compose.metrics.yml up -d prometheus grafana

# 3. Открыть Grafana → http://localhost:3001 → admin/admin.
#    Dashboard "Credit Assistant — Operations" уже provision'ен.

# 4. Проверить scrape:
curl -fsS http://localhost:9090/-/healthy   # Prometheus health
curl -fsS http://localhost:8000/metrics | head -20  # raw metrics
```

Smoke событий для верификации dashboard'а:

```bash
# Сгенерить нагрузку — несколько досье через UI либо seed script:
docker compose exec api bash -c "cd /app/src && uv run --no-sync python -m scripts.seed_demo_borrowers"

# Дёрнуть /api/system/health 100 раз для красивых HTTP-панелей:
for i in {1..100}; do curl -sf http://localhost:8000/health >/dev/null; done
```

Через 30-60 секунд panels заполнятся.

---

## 3. Dashboard tour

`deploy/metrics/grafana/dashboards/credit-assistant.json` — bundled, version-controlled.

**Top row (stat panels):**

* **Request rate** — `sum(rate(http_requests_total[5m]))`. Norm baseline ≈ 0.1-1
  req/s для bank-internal install с 10-20 analysts.
* **Error rate (5xx)** — порог alert: >0.1 req/s = yellow, >1 = red.
* **Latency p50/p95/p99** — bank-internal SLO target: p99 < 2s
  (включая dossier list и search).

**Middle row:**

* **PDF render p50/p95** — WeasyPrint normal p95 ≈ 5-10s (зависит от
  размера досье + chart count). Spike до >20s → регрессия (новый шрифт?
  сложный template?).
* **Parser warnings rate by format** — каждый ненулевой spike сигнализирует
  что Soliq поменял layout xltx. Trigger investigate — открыть последний
  upload + сравнить с `tests/fixtures/soliq_xltx/`.

**Bottom row:**

* **Red flags fired by severity** — критичные сигналы fraud detection.
  Резкий всплеск `critical` per hour (>10/h) → либо real fraud wave,
  либо false-positive после rules engine update — проверить.
* **Inflight HTTP requests** — concurrency. Норма для bank-internal ≈ 1-5;
  >50 — что-то висит (медленный handler / DB lock / external API timeout).

---

## 4. Production deploy

### Bundled с основным stack

Caddy reverse-proxy раздаёт grafana на отдельном subdomain:

```
grafana.{$CADDY_DOMAIN} {
  reverse_proxy grafana:3000
  header X-Frame-Options "DENY"
}
```

Prometheus наружу **не** экспонится — scrape-only через compose-network.
Если bank-IT хочет прямой доступ для своего alert-manager — добавить
basic-auth через `web.config.file`.

### Отдельный host

Если банк уже имеет Prometheus, направить scrape job на наш api:

```yaml
scrape_configs:
  - job_name: credit-api
    static_configs:
      - targets: ["credit-api.bank.uz:8000"]
    metrics_path: /metrics
    scheme: https
    basic_auth: ...   # если за Caddy basic-auth
```

Bundled Prometheus/Grafana можно тогда не поднимать — переменная
`METRICS_ENABLED=true` достаточна.

### Storage

`--storage.tsdb.retention.time=30d` в `docker-compose.metrics.yml`.
Approx 5 GB disk при 0.1-1 req/s baseline. Tweakable.

---

## 5. Alert rules

В текущей версии alerting настраивается **в Grafana UI** (Alerting →
New alert rule). Не в коде repo — trade-off ради скорости iteration.

Минимальный pack для bank-pilot:

| Alert | Условие | Severity | Канал |
|---|---|---|---|
| API down | `up{job="credit-api"} == 0 for 1m` | critical | email + Slack |
| Error rate high | `rate(http_requests_total{status_code=~"5.."}[5m]) > 0.5` | critical | email |
| Latency degraded | `histogram_quantile(0.95, ...) > 5` for 5m | warning | email |
| PDF render slow | `histogram_quantile(0.95, pdf_render_duration_seconds_bucket) > 20` for 10m | warning | email |
| Parser warnings spike | `rate(parser_warnings_total[10m]) > 1` | warning | email |
| Critical red flags spike | `rate(red_flags_fired_total{severity="critical"}[1h]) > 0.01` | info | email |

**Email** — через Grafana SMTP, прокидывается через env (`GF_SMTP_*`).

Post-demo: переехать на AlertManager + `prometheus rules` files в git
(см. ADR-0023 Out of scope).

---

## 6. Cross-reference metrics ↔ logs ↔ errors

Сценарий "что-то взорвалось":

1. **Grafana** → видим spike в error rate / latency.
2. **GlitchTip** (T3.1) → находим конкретный issue + `request_id` tag.
3. `journalctl -u credit-assistant | grep <request_id>` (T3.2) → полная
   structured-log цепочка.
4. `SELECT * FROM audit_log WHERE request_id = '<...>'` → действия
   пользователя за этим request.

Это 3-layer observability: metrics ловят trend, errors дают stacktrace,
logs/audit дают reproduction path.

---

## 7. Troubleshooting

### `/metrics` отдаёт 404

`METRICS_ENABLED=true` в `.env`. Перезапустить api: `docker compose up
-d --build api` (не `restart` — нужен rebuild конфиг).

### Prometheus не scrape'ит api

```bash
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {labels, health, lastError}'
```

Если `health: "down"` + `lastError: connection refused` → api не на
ожидаемом DNS-имени. Проверить compose network: `docker compose exec
prometheus wget -O- http://api:8000/metrics | head`.

### Grafana dashboard пустой

* Datasource Prometheus провален: Configuration → Data Sources → проверить
  URL `http://prometheus:9090` + Save & Test.
* Time range за пределами data: переключить на "Last 15m".

### Custom метрика отсутствует в `/metrics`

Counter эмитит точку только после первой `.inc()`. До этого — `0`,
не показывается. Дёрнуть соответствующее действие хотя бы раз
(сгенерить PDF / залить xltx / запустить scoring) чтобы counter
зарегистрировался.

### High cardinality warning

`http_requests_total{handler=...}` лейбл `handler` — это FastAPI path
template (`/api/bank/borrowers/{inn}`). Если случайно появился raw INN
в label — это cardinality explosion. Investigate: `should_ignore_untemplated=True`
в `Instrumentator` config должен это предотвратить.

---

## 8. Operational checklist

**Daily:**

* [ ] Grafana dashboard опрошен на anomalies (5min).
* [ ] Error rate panel — spikes выше baseline?

**Weekly:**

* [ ] Alert rules review — false-positive thresholds.
* [ ] Parser warnings rate — есть ли стабильный baseline > 0? (signal на
  новый Soliq layout, который проскользнул).

**Monthly:**

* [ ] Grafana version upgrade.
* [ ] Prometheus retention — фактический disk usage vs предсказание.
* [ ] Dashboard provisioning sync (если кто-то менял в UI — экспортнуть
  JSON обратно в `deploy/metrics/grafana/dashboards/credit-assistant.json`
  через PR).

**Quarterly:**

* [ ] SLO review (latency / error budget). Если регулярно нарушаем —
  capacity scaling либо оптимизация.

---

## 9. References

* ADR-0023 — Metrics decision rationale.
* `src/infrastructure/observability/metrics.py` — instrumentation + custom counters.
* `docker-compose.metrics.yml` — Prometheus + Grafana sidecars.
* `deploy/metrics/` — auto-provisioning configs + dashboard.
* `docs/operations/observability.md` — GlitchTip error tracking (T3.1).
* `docs/operations/db-backup.md` — backup runbook (T3.4).
* Prometheus query language: <https://prometheus.io/docs/prometheus/latest/querying/basics/>
* Grafana provisioning: <https://grafana.com/docs/grafana/latest/administration/provisioning/>
