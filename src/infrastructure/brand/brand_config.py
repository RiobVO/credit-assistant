"""Brand config resolver: backend mirror фронтовому ``resolveBrand()``.

Источник — те же ``config/brands/<id>.json`` (single source of truth для
обоих стеков, см. CA-066 / ADR-0011). Выбор brand-id через env ``BRAND_ID``,
fallback на ``default``.

Используется WeasyPrintPdfRenderer для tenant-aware шапки PDF (Phase 10):
имя банка, tagline, logoMark, primary-цвет, primaryInk. Никакого hex'а в
шаблоне — только token references из этого конфига.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from application.dto.brand_config import BrandConfig

# config/brands лежит в корне репо (рядом с config/rules). Резолвим
# относительно этого модуля: src/infrastructure/brand/ → ../../../config/brands
_BRANDS_DIR = Path(__file__).resolve().parents[3] / "config" / "brands"
_DEFAULT_BRAND_ID = "default"


class BrandConfigError(ValueError):
    """Brand-config файл отсутствует или повреждён."""


def load_brand(brand_id: str | None = None) -> BrandConfig:
    """Резолвит brand-config по id. None → env ``BRAND_ID`` → ``default``.

    Raises ``BrandConfigError`` если файл отсутствует или невалиден.
    """
    resolved_id = brand_id or os.getenv("BRAND_ID", _DEFAULT_BRAND_ID)
    path = _BRANDS_DIR / f"{resolved_id}.json"
    if not path.exists():
        raise BrandConfigError(f"brand config not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BrandConfigError(f"invalid JSON in {path}: {exc}") from exc

    try:
        return BrandConfig(
            id=raw["id"],
            name=raw["name"],
            tagline=raw["tagline"],
            logo_mark=raw["logoMark"],
            primary=raw["primary"],
            primary_hover=raw["primaryHover"],
            primary_soft=raw["primarySoft"],
            primary_ink=raw["primaryInk"],
            primary_ring=raw["primaryRing"],
        )
    except KeyError as exc:
        raise BrandConfigError(f"missing key in {path}: {exc}") from exc
