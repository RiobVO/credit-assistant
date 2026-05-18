"""Unit-тест brand_config резолвера."""

from __future__ import annotations

import json
from pathlib import Path

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


def test_missing_brand_raises() -> None:
    with pytest.raises(BrandConfigError, match="brand config not found"):
        load_brand("does-not-exist")


# CA-DS6/7/8: support + business_hours optional sections.


def test_default_brand_has_support_and_business_hours() -> None:
    """default.json и uzbekbank.json содержат support/businessHours sections."""
    brand = load_brand("default")
    assert brand.support is not None
    assert brand.support.phone.startswith("+998")
    assert brand.support.phone_tel.startswith("tel:")
    assert "@" in brand.support.email
    assert brand.support.slack.channel.startswith("#")
    assert brand.support.docs.url.startswith("https://")
    assert brand.support.compliance_phone
    assert brand.business_hours is not None
    assert brand.business_hours.timezone == "Asia/Tashkent"
    assert brand.business_hours.weekdays.start == "09:00"


def _write_brand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]
) -> None:
    """Перенаправляет _BRANDS_DIR на временный каталог с данным payload."""
    target_dir = tmp_path / "config" / "brands"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / f"{payload['id']}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    monkeypatch.setattr(
        "infrastructure.brand.brand_config._BRANDS_DIR", target_dir
    )


_MINIMAL_BRAND: dict[str, object] = {
    "id": "minimal",
    "name": "Minimal",
    "tagline": "T",
    "logoMark": "M",
    "primary": "#000000",
    "primaryHover": "#000000",
    "primarySoft": "#000000",
    "primaryInk": "#000000",
    "primaryRing": "rgba(0,0,0,1)",
}


def test_brand_without_optional_sections_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Brand-config без support/businessHours остаётся валидным."""
    _write_brand(tmp_path, monkeypatch, _MINIMAL_BRAND)
    brand = load_brand("minimal")
    assert brand.support is None
    assert brand.business_hours is None


def test_invalid_support_missing_key_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = dict(_MINIMAL_BRAND)
    payload["support"] = {
        "phone": "+998",
        "phoneTel": "tel:+998",
        "email": "a@b.uz",
        # Missing 'slack', 'docs', 'compliancePhone'.
    }
    _write_brand(tmp_path, monkeypatch, payload)
    with pytest.raises(BrandConfigError, match="missing key in support"):
        load_brand("minimal")


def test_invalid_business_hours_missing_key_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = dict(_MINIMAL_BRAND)
    payload["businessHours"] = {
        "timezone": "Asia/Tashkent",
        # Missing 'weekdays'.
    }
    _write_brand(tmp_path, monkeypatch, payload)
    with pytest.raises(BrandConfigError, match="missing key in businessHours"):
        load_brand("minimal")


def test_support_not_an_object_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = dict(_MINIMAL_BRAND)
    payload["support"] = "not an object"
    _write_brand(tmp_path, monkeypatch, payload)
    with pytest.raises(BrandConfigError, match="'support' must be an object"):
        load_brand("minimal")


# T0.4 / ADR-0015: optional defaultLang.


def test_brand_default_lang_none_when_absent() -> None:
    """default.json без defaultLang → None (endpoint fallback на 'ru')."""
    brand = load_brand("default")
    assert brand.default_lang is None


def test_brand_default_lang_parsed_when_uz(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = dict(_MINIMAL_BRAND)
    payload["defaultLang"] = "uz"
    _write_brand(tmp_path, monkeypatch, payload)
    brand = load_brand("minimal")
    assert brand.default_lang == "uz"


def test_brand_default_lang_invalid_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = dict(_MINIMAL_BRAND)
    payload["defaultLang"] = "en"
    _write_brand(tmp_path, monkeypatch, payload)
    with pytest.raises(BrandConfigError, match="defaultLang"):
        load_brand("minimal")
