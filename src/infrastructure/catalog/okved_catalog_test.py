"""Unit-тесты OKVED catalog loader (CA-DS17)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from application.dto.okved import OkvedEntry
from infrastructure.catalog.okved_catalog import (
    OkvedCatalog,
    OkvedCatalogError,
    default_catalog,
    load_catalog,
)


def test_load_default_catalog_returns_all_msb_codes() -> None:
    """Default catalog содержит ≥17 кодов МСБ-сегмента (исторический минимум)."""
    catalog = load_catalog()
    assert len(catalog.list()) >= 17


def test_default_catalog_contains_pdf_legacy_codes() -> None:
    """Все 17 кодов из legacy ``_OKVED_LABELS`` в pdf_renderer должны быть
    представлены в catalog (no-regression при удалении hardcoded dict)."""
    catalog = load_catalog()
    legacy_codes = {
        "47.11", "47.19", "10.71", "13.10", "14.13",
        "41.20", "43.39", "45.20", "46.31", "46.39",
        "49.41", "52.10", "56.10", "62.01", "68.20",
        "85.10", "86.21",
    }
    actual = {entry.code for entry in catalog.list()}
    missing = legacy_codes - actual
    assert not missing, f"PDF legacy codes missing from catalog: {sorted(missing)}"


def test_get_known_code_returns_entry() -> None:
    catalog = load_catalog()
    entry = catalog.get("47.11")
    assert entry is not None
    assert entry.code == "47.11"
    assert entry.short_ru
    assert entry.full_ru
    assert entry.short_uz
    assert entry.full_uz


def test_get_unknown_code_returns_none() -> None:
    catalog = load_catalog()
    assert catalog.get("99.99") is None
    assert catalog.get("") is None


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(OkvedCatalogError, match="not found"):
        load_catalog(tmp_path / "does-not-exist.json")


def test_load_invalid_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    with pytest.raises(OkvedCatalogError, match="invalid JSON"):
        load_catalog(bad)


def test_load_missing_items_key_raises(tmp_path: Path) -> None:
    bad = tmp_path / "no_items.json"
    bad.write_text(json.dumps({"version": 1}), encoding="utf-8")
    with pytest.raises(OkvedCatalogError, match="missing or non-list 'items'"):
        load_catalog(bad)


def test_load_missing_field_raises(tmp_path: Path) -> None:
    bad = tmp_path / "missing_field.json"
    bad.write_text(
        json.dumps(
            {
                "version": 1,
                "items": [{"code": "47.11", "short_ru": "x", "full_ru": "y"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(OkvedCatalogError, match="missing key"):
        load_catalog(bad)


def test_load_non_object_item_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad_item.json"
    bad.write_text(json.dumps({"version": 1, "items": ["not-an-object"]}), encoding="utf-8")
    with pytest.raises(OkvedCatalogError, match="not an object"):
        load_catalog(bad)


def test_default_catalog_singleton() -> None:
    """``default_catalog()`` должен возвращать один и тот же instance
    (lru_cache singleton — критично для startup-cost backend'а)."""
    a = default_catalog()
    b = default_catalog()
    assert a is b


def test_catalog_constructable_from_entries() -> None:
    """Прямой конструктор для unit-тестов в др. модулях."""
    entries = (
        OkvedEntry(
            code="01.11",
            short_ru="Тестовый",
            full_ru="Тестовый код",
            short_uz="Test",
            full_uz="Test kod",
        ),
    )
    catalog = OkvedCatalog(entries)
    assert catalog.get("01.11") is not None
    assert catalog.get("99.99") is None
    assert len(catalog.list()) == 1
