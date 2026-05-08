"""Unit-тест brand_config резолвера."""

from __future__ import annotations

import pytest

from application.dto.brand_config import BrandConfig
from infrastructure.brand.brand_config import BrandConfigError, load_brand


def test_load_default_brand() -> None:
    brand = load_brand("default")
    assert isinstance(brand, BrandConfig)
    assert brand.id == "default"
    assert brand.name == "Credit Assistant"
    assert brand.primary.startswith("#")
    assert brand.logo_mark


def test_load_uzbekbank_brand() -> None:
    brand = load_brand("uzbekbank")
    assert brand.id == "uzbekbank"
    assert brand.name == "Uzbekbank Credit"
    assert brand.logo_mark == "UB"
    assert brand.primary == "#CC785C"


def test_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAND_ID", "uzbekbank")
    brand = load_brand()
    assert brand.id == "uzbekbank"


def test_missing_brand_raises() -> None:
    with pytest.raises(BrandConfigError, match="brand config not found"):
        load_brand("does-not-exist")


def test_default_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BRAND_ID", raising=False)
    brand = load_brand()
    assert brand.id == "default"
