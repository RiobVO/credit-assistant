"""Unit-тесты для `create_app` startup-валидации.

T1.4.1: `_validate_runtime_config(settings)` обобщает startup-assert'ы.
Сейчас покрывает:
- BRAND_ID: соответствующий `config/brands/<id>.json` обязан существовать
  и парситься. Crash на boot, если файла нет или ID mismatch.
- PII_ENC_KEYS (T1.3 / ADR-0017): обязателен в staging/prod.

Crash-on-boot гарантирует, что misconfigured production не запустится
молча с пустым tenant-контекстом или decryption-passthrough.
"""

from __future__ import annotations

import pytest

from config.settings import Settings
from interfaces.api.app import create_app


def _make_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "local",
        "app_mode": "accountant",
        "brand_id": "default",
        "pii_enc_keys": None,
        "uptime_collector_enabled": False,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_create_app_passes_with_default_brand() -> None:
    settings = _make_settings()
    app = create_app(settings=settings)
    assert app is not None


def test_create_app_passes_with_uzbekbank_brand() -> None:
    settings = _make_settings(brand_id="uzbekbank")
    app = create_app(settings=settings)
    assert app is not None


def test_create_app_raises_when_brand_config_missing() -> None:
    settings = _make_settings(brand_id="ghost-bank-does-not-exist")
    with pytest.raises(RuntimeError, match="BRAND_ID"):
        create_app(settings=settings)


def test_create_app_raises_when_pii_keys_missing_in_prod() -> None:
    settings = _make_settings(app_env="prod", pii_enc_keys=None)
    with pytest.raises(RuntimeError, match="PII_ENC_KEYS"):
        create_app(settings=settings)


def test_create_app_raises_when_pii_keys_missing_in_staging() -> None:
    settings = _make_settings(app_env="staging", pii_enc_keys=None)
    with pytest.raises(RuntimeError, match="PII_ENC_KEYS"):
        create_app(settings=settings)


def test_create_app_passes_when_pii_keys_set_in_prod() -> None:
    """Production с обоими ключами загружается."""
    fake_fernet_key = "_" * 43 + "="
    settings = _make_settings(
        app_env="prod",
        pii_enc_keys=fake_fernet_key,
        brand_id="default",
    )
    app = create_app(settings=settings)
    assert app is not None
