"""Unit-тесты для T3.1.1 sentry init + PII scrubbing."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
import sentry_sdk

from config.settings import Settings
from infrastructure.observability.sentry import (
    _before_send,
    _scrub_dict,
    _scrub_string,
    init_sentry,
)


@pytest.fixture(autouse=True)
def _reset_sentry() -> Iterator[None]:
    """Каждый тест начинает с чистого Hub — иначе init из соседнего теста
    оставляет client активным и (с fake DSN) пытается слать events.

    Teardown переинициализирует SDK с пустым DSN → клиент становится noop
    и не пытается flush'нуть pending events на выходе."""
    sentry_sdk.get_global_scope().clear()
    yield
    # Tear-down: deactivate transport (без этого fake DSN тестов остаётся
    # активным, и atexit-flush пытается стучаться на localhost).
    sentry_sdk.init(dsn=None)


def _make_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "local",
        "app_mode": "accountant",
        "brand_id": "default",
        "pii_enc_keys": None,
        "sentry_dsn": None,
        "uptime_collector_enabled": False,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_init_sentry_with_none_dsn_is_noop() -> None:
    settings = _make_settings(sentry_dsn=None)
    init_sentry(settings)
    client = sentry_sdk.get_client()
    assert not client.is_active(), "DSN=None должен оставить SDK неактивным"


def test_init_sentry_with_dsn_activates_client() -> None:
    fake_dsn = "https://pubkey@localhost/1"
    settings = _make_settings(sentry_dsn=fake_dsn, sentry_environment="dev")
    init_sentry(settings)
    client = sentry_sdk.get_client()
    assert client.is_active()
    assert client.options["environment"] == "dev"
    assert client.options["traces_sample_rate"] == 0.0
    assert client.options["send_default_pii"] is False


def test_scrub_string_masks_email() -> None:
    out = _scrub_string("user a@bank.uz reported error")
    assert "a@bank.uz" not in out
    assert "@bank.uz" in out  # маска вида ***@bank.uz


def test_scrub_dict_drops_password_like_keys() -> None:
    out = _scrub_dict({"password": "x", "jwt_secret": "y", "ok": "z"})
    assert out["password"] == "[scrubbed]"
    assert out["jwt_secret"] == "[scrubbed]"
    assert out["ok"] == "z"


def test_scrub_dict_masks_emails_in_values() -> None:
    out = _scrub_dict({"user": "alex@bank.uz logged in"})
    assert "alex@bank.uz" not in out["user"]


def test_before_send_drops_request_body_and_cookies() -> None:
    event: dict[str, Any] = {
        "request": {
            "data": {"password": "secret"},
            "cookies": "ca_access=jwt-value",
            "headers": {"Authorization": "Bearer XXX"},
        }
    }
    result = _before_send(event, {})  # type: ignore[arg-type]
    assert result is not None
    request = cast(dict[str, Any], result["request"])
    assert "data" not in request
    assert "cookies" not in request
    assert request["headers"]["Authorization"] == "[scrubbed]"


def test_before_send_masks_emails_in_breadcrumbs() -> None:
    event: dict[str, Any] = {
        "breadcrumbs": {
            "values": [
                {"message": "user b@bank.uz did X", "data": {"email": "c@bank.uz"}},
            ]
        }
    }
    result = _before_send(event, {})  # type: ignore[arg-type]
    assert result is not None
    breadcrumbs = cast(dict[str, Any], result["breadcrumbs"])
    crumb = breadcrumbs["values"][0]
    assert "b@bank.uz" not in crumb["message"]
    assert "c@bank.uz" not in crumb["data"].get("email", "")
