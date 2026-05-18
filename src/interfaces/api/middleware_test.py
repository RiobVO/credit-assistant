"""Тесты T3.2.2 для ``RequestIDMiddleware`` — X-Request-ID echo / auto-gen +
bind/unbind ``structlog.contextvars`` вокруг handler-call."""

from __future__ import annotations

import re

import pytest
import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from structlog.contextvars import clear_contextvars, get_contextvars

from interfaces.api.middleware import RequestIDMiddleware

HEX32 = re.compile(r"^[0-9a-f]{32}$")


@pytest.fixture(autouse=True)
def _clean_contextvars() -> None:
    clear_contextvars()


def _build_app(probe: dict[str, str | None]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/probe")
    def probe_endpoint() -> dict[str, str]:
        ctx = get_contextvars()
        probe["bound_request_id"] = ctx.get("request_id")
        return {"ok": "1"}

    return app


def test_missing_header_generates_hex_uuid() -> None:
    probe: dict[str, str | None] = {}
    app = _build_app(probe)
    with TestClient(app) as client:
        response = client.get("/probe")

    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID")
    assert rid is not None
    assert HEX32.match(rid), f"expected 32 hex chars, got {rid!r}"


def test_existing_header_echoed_back() -> None:
    probe: dict[str, str | None] = {}
    app = _build_app(probe)
    with TestClient(app) as client:
        response = client.get("/probe", headers={"X-Request-ID": "deadbeef"})

    assert response.headers["X-Request-ID"] == "deadbeef"


def test_bind_active_during_request_matches_response_header() -> None:
    probe: dict[str, str | None] = {}
    app = _build_app(probe)
    with TestClient(app) as client:
        response = client.get("/probe", headers={"X-Request-ID": "trace-xyz"})

    assert probe["bound_request_id"] == "trace-xyz"
    assert response.headers["X-Request-ID"] == "trace-xyz"


def test_unbind_after_response_isolates_requests() -> None:
    probe: dict[str, str | None] = {}
    app = _build_app(probe)
    with TestClient(app) as client:
        client.get("/probe", headers={"X-Request-ID": "first-rid"})
        # Внутри handler'а первого запроса request_id был "first-rid".
        # После ответа contextvars должны быть очищены — следующий запрос
        # без header должен сгенерировать **новый** id, не унаследовать.
        probe.clear()
        response = client.get("/probe")

    rid = response.headers["X-Request-ID"]
    assert rid != "first-rid"
    assert probe["bound_request_id"] == rid


def test_request_id_set_as_sentry_tag() -> None:
    """T3.1: request_id попадает в Sentry scope как tag — для GlitchTip
    фильтрации events по correlation_id."""
    import sentry_sdk

    captured: dict[str, str] = {}

    def _fake_send(event: object, _hint: object) -> object:
        # Sentry SDK noop без DSN; для test'а перехватываем через scope hook.
        return None

    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/probe")
    def probe_endpoint() -> dict[str, str]:
        tags = sentry_sdk.get_current_scope()._tags
        captured["request_id"] = tags.get("request_id", "")
        return {"ok": "1"}

    _ = _fake_send  # silence unused-warning for placeholder transport
    with TestClient(app) as client:
        client.get("/probe", headers={"X-Request-ID": "tag-test-123"})

    assert captured["request_id"] == "tag-test-123"


def test_structlog_logger_emits_request_id_during_request(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Проверка, что bind_contextvars из middleware виден structlog-logger'у
    внутри handler-call — это foundation для T3.2.3 integration."""
    from config.logging import configure_logging

    configure_logging(level="INFO")
    logger = structlog.get_logger("ca.test.middleware")

    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/log")
    def log_endpoint() -> dict[str, str]:
        logger.info("handler_event")
        return {"ok": "1"}

    with caplog.at_level("INFO"), TestClient(app) as client:
        response = client.get("/log", headers={"X-Request-ID": "log-rid-7"})

    rid = response.headers["X-Request-ID"]
    assert rid == "log-rid-7"
    matched = [r for r in caplog.records if getattr(r, "request_id", None) == rid]
    assert matched, "ожидали хотя бы один log record с request_id из middleware"
