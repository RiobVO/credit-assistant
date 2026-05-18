"""T3.3 — Prometheus metrics: auto-instrumentation + custom counters/histograms.

Auto через ``prometheus-fastapi-instrumentator``:
* HTTP request latency (histogram with default buckets).
* HTTP response status counter.
* Inflight requests gauge.

Custom (под бизнес-метрики Credit Assistant):
* ``pdf_render_duration_seconds`` — гистограмма времени WeasyPrint rendering.
* ``parser_warnings_total`` — counter по типу xltx-формата (parse_warnings
  не fatal, но важно мониторить регрессии форматов Soliq).
* ``red_flags_fired_total`` — counter по severity (critical/high/medium/low),
  signal для anomaly detection (всплеск critical = что-то изменилось в
  rules engine либо данных).

Endpoint: ``GET /metrics`` (Prometheus exposition format). Mount на root —
scraper типично pull'ит ``/metrics`` без префикса.
"""

from __future__ import annotations

from fastapi import FastAPI
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

# Custom метрики экспортируются как module-level singletons — Prometheus
# client требует единственной регистрации на метрику в default registry.

pdf_render_duration = Histogram(
    "pdf_render_duration_seconds",
    "Время WeasyPrint PDF-рендера досье в секундах",
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0),
)

parser_warnings_total = Counter(
    "parser_warnings_total",
    "Cell-level warnings от Soliq xltx parser'ов (best-effort семантика)",
    labelnames=("format",),  # vat_declaration / vat_registry_ilova / form_1 / form_2 / profit_tax
)

red_flags_fired_total = Counter(
    "red_flags_fired_total",
    "Сработавшие red-flag rules per scoring run",
    labelnames=("severity",),  # critical / high / medium / low
)


def setup_prometheus(app: FastAPI) -> None:
    """Wire Prometheus instrumentator to FastAPI app + register /metrics endpoint.

    Вызывается в ``create_app`` только когда ``settings.metrics_enabled=True``.
    """
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        excluded_handlers=["/metrics", "/health"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="http_inprogress_requests",
        inprogress_labels=False,
    )
    instrumentator.instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        should_gzip=False,
    )
