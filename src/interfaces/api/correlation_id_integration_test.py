"""T3.2.3 integration: RequestIDMiddleware wired в create_app → request_id
проникает в structlog/stdlib records внутри handler-цепочки.

In-src placement: не требует testcontainers Postgres — accountant mode +
``/health`` endpoint, без БД-зависимостей. Полный stack от middleware до
``LogRecord``-factory обходится одним FastAPI app.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from structlog.contextvars import clear_contextvars

from config.settings import Settings
from interfaces.api.app import create_app


def _make_settings() -> Settings:
    return Settings(
        app_env="local",
        app_mode="accountant",
        brand_id="default",
        pii_enc_keys=None,
        uptime_collector_enabled=False,
    )


@pytest.fixture(autouse=True)
def _isolate_contextvars() -> None:
    clear_contextvars()


def test_request_id_present_in_health_response_header() -> None:
    """Middleware на месте — auto-gen header."""
    app = create_app(_make_settings())
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID")
    assert rid is not None and len(rid) == 32


def test_request_id_echoed_when_client_provides_header() -> None:
    app = create_app(_make_settings())
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "client-abc"})

    assert response.headers["X-Request-ID"] == "client-abc"


def test_request_id_propagates_to_handler_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Лог внутри health-handler видит request_id из middleware."""
    app = create_app(_make_settings())

    with caplog.at_level(logging.INFO), TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "trace-007"})

    rid = response.headers["X-Request-ID"]
    assert rid == "trace-007"

    matched = [r for r in caplog.records if getattr(r, "request_id", None) == rid]
    assert matched, (
        "ожидали хотя бы один LogRecord с request_id='trace-007' — middleware "
        "не bind'нул contextvars или конфигурация logging не подхватила factory"
    )


def test_request_ids_isolated_between_sequential_requests() -> None:
    """Auto-gen id уникален per-request — unbind в finally работает."""
    app = create_app(_make_settings())
    with TestClient(app) as client:
        r1 = client.get("/health")
        r2 = client.get("/health")

    assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]
