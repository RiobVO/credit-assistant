"""T3.3 unit-тесты для Prometheus metrics."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import generate_latest

from infrastructure.observability.metrics import (
    parser_warnings_total,
    pdf_render_duration,
    red_flags_fired_total,
    setup_prometheus,
)


def test_setup_prometheus_exposes_metrics_endpoint() -> None:
    app = FastAPI()
    setup_prometheus(app)

    @app.get("/probe")
    def _probe() -> dict[str, str]:
        return {"ok": "1"}

    with TestClient(app) as client:
        client.get("/probe")
        resp = client.get("/metrics")

    assert resp.status_code == 200
    body = resp.text
    # Default request counter / latency histogram наполнились.
    assert "http_request_duration_seconds" in body or "http_requests_total" in body


def test_pdf_render_duration_records_observation() -> None:
    pdf_render_duration.observe(2.5)
    # generate_latest подбирает все registered collectors из default registry.
    output = generate_latest().decode("utf-8")
    assert "pdf_render_duration_seconds" in output


def test_parser_warnings_counter_increments_per_format() -> None:
    parser_warnings_total.labels(format="form_2").inc()
    parser_warnings_total.labels(format="form_2").inc()
    parser_warnings_total.labels(format="profit_tax").inc()

    output = generate_latest().decode("utf-8")
    assert 'parser_warnings_total{format="form_2"}' in output
    assert 'parser_warnings_total{format="profit_tax"}' in output


def test_red_flags_counter_increments_per_severity() -> None:
    red_flags_fired_total.labels(severity="critical").inc()
    red_flags_fired_total.labels(severity="high").inc(3)

    output = generate_latest().decode("utf-8")
    assert 'red_flags_fired_total{severity="critical"}' in output
    assert 'red_flags_fired_total{severity="high"}' in output


def test_metrics_endpoint_returns_prometheus_format() -> None:
    """Verify content-type Prometheus exposition format."""
    app = FastAPI()
    setup_prometheus(app)

    with TestClient(app) as client:
        resp = client.get("/metrics")

    assert resp.status_code == 200
    # Prometheus client returns text/plain; version=0.0.4
    assert resp.headers["content-type"].startswith("text/plain")
