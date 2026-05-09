"""Unit-тесты USD/UZS rate loader (CA-DS24)."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from infrastructure.catalog.exchange_rates import (
    ExchangeRateError,
    load_usd_uzs_rate,
)


def test_load_default_rate_from_file() -> None:
    """Default JSON-файл содержит валидный rate, asof, source."""
    rate = load_usd_uzs_rate()
    assert rate.rate > 0
    assert rate.source == "manual"
    assert isinstance(rate.asof, date)


def test_env_override_takes_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USD_UZS_RATE", "13000")
    rate = load_usd_uzs_rate()
    assert rate.rate == Decimal("13000")
    assert rate.source == "env"
    # asof остаётся из файла — env не несёт даты.
    assert isinstance(rate.asof, date)


def test_env_empty_string_falls_back_to_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Пустой env — игнорируется, fallback на JSON."""
    monkeypatch.setenv("USD_UZS_RATE", "")
    rate = load_usd_uzs_rate()
    assert rate.source == "manual"


def test_env_invalid_decimal_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USD_UZS_RATE", "not-a-number")
    with pytest.raises(ExchangeRateError, match="not a decimal"):
        load_usd_uzs_rate()


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ExchangeRateError, match="not found"):
        load_usd_uzs_rate(tmp_path / "does-not-exist.json")


def test_load_invalid_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ExchangeRateError, match="invalid JSON"):
        load_usd_uzs_rate(bad)


def test_load_missing_required_field_raises(tmp_path: Path) -> None:
    bad = tmp_path / "missing.json"
    bad.write_text(json.dumps({"version": 1, "asof": "2026-05-15"}), encoding="utf-8")
    with pytest.raises(ExchangeRateError, match="invalid rate fields"):
        load_usd_uzs_rate(bad)


def test_load_invalid_decimal_in_file_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad_decimal.json"
    bad.write_text(
        json.dumps({"version": 1, "usd_uzs": "not-a-number", "asof": "2026-05-15"}),
        encoding="utf-8",
    )
    with pytest.raises(ExchangeRateError, match="invalid rate fields"):
        load_usd_uzs_rate(bad)


def test_load_invalid_asof_in_file_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad_asof.json"
    bad.write_text(
        json.dumps({"version": 1, "usd_uzs": "12575", "asof": "not-a-date"}),
        encoding="utf-8",
    )
    with pytest.raises(ExchangeRateError, match="invalid rate fields"):
        load_usd_uzs_rate(bad)
