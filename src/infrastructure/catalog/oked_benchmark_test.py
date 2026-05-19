"""Tests для OkedBenchmarkCatalog (ADR-0024 / Commit 3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infrastructure.catalog.oked_benchmark import (
    OkedBenchmarkCatalogError,
    load_catalog,
)


def test_default_catalog_loads() -> None:
    """config/benchmarks/oked-uz.json парсится без ошибок."""
    catalog = load_catalog()
    assert len(catalog.list()) == 7  # секции A/C/F/G/H/I/J


def test_by_oked_code_43_39_resolves_to_construction() -> None:
    """ADR-0024 bug fix: ОКЭД 43.39 → bucket F (Строительство), не G."""
    catalog = load_catalog()
    bucket = catalog.by_oked_code("43.39")
    assert bucket is not None
    assert bucket.code_prefix == "F"
    assert "троительство" in bucket.name_ru.lower() or "Строительство" in bucket.name_ru


def test_by_oked_code_46_30_resolves_to_trade() -> None:
    """G-секция: оптовая торговля (46) маппится в bucket G."""
    catalog = load_catalog()
    bucket = catalog.by_oked_code("46.30")
    assert bucket is not None
    assert bucket.code_prefix == "G"


def test_by_oked_code_unknown_returns_none() -> None:
    """Неизвестный код (например, K — финансы, не в catalog) → None."""
    catalog = load_catalog()
    assert catalog.by_oked_code("64.19") is None


def test_by_oked_code_empty_returns_none() -> None:
    catalog = load_catalog()
    assert catalog.by_oked_code("") is None


def test_medians_all_null_by_design() -> None:
    """ADR-0024 policy: все медианы null до commission-исследования."""
    catalog = load_catalog()
    for bucket in catalog.list():
        assert bucket.median.roe_pct is None
        assert bucket.median.net_margin_pct is None
        assert bucket.median.asset_turnover is None
        assert bucket.median.debt_to_equity is None


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(OkedBenchmarkCatalogError, match="not found"):
        load_catalog(tmp_path / "does_not_exist.json")


def test_invalid_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not a json", encoding="utf-8")
    with pytest.raises(OkedBenchmarkCatalogError, match="invalid JSON"):
        load_catalog(bad)


def test_missing_buckets_key_raises(tmp_path: Path) -> None:
    bad = tmp_path / "no_buckets.json"
    bad.write_text(json.dumps({"version": "1.0"}), encoding="utf-8")
    with pytest.raises(OkedBenchmarkCatalogError, match="missing or non-list 'buckets'"):
        load_catalog(bad)


def test_missing_bucket_key_raises(tmp_path: Path) -> None:
    bad = tmp_path / "missing_key.json"
    bad.write_text(
        json.dumps(
            {
                "version": "1.0",
                "buckets": [{"code_prefix": "F"}],  # no oked_subsections, name_ru, etc.
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(OkedBenchmarkCatalogError, match="missing key"):
        load_catalog(bad)
