"""Brand config resolver: backend mirror фронтовому ``resolveBrand()``.

Источник — те же ``config/brands/<id>.json`` (single source of truth для
обоих стеков, см. CA-066 / ADR-0011). Выбор brand-id через env ``BRAND_ID``,
fallback на ``default``.

Используется WeasyPrintPdfRenderer для tenant-aware шапки PDF (Phase 10):
имя банка, tagline, logoMark, primary-цвет, primaryInk. Никакого hex'а в
шаблоне — только token references из этого конфига.

CA-DS6/7/8: support + business_hours — optional sections, парсятся в
None если отсутствуют. PDF их не использует; только frontend HelpView.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from application.dto.brand_config import (
    BrandConfig,
    BusinessHours,
    DocsSupport,
    SlackSupport,
    SupportConfig,
    WeekdaysHours,
)

# config/brands лежит в корне репо (рядом с config/rules). Резолвим
# относительно этого модуля: src/infrastructure/brand/ → ../../../config/brands
_BRANDS_DIR = Path(__file__).resolve().parents[3] / "config" / "brands"
_DEFAULT_BRAND_ID = "default"


class BrandConfigError(ValueError):
    """Brand-config файл отсутствует или повреждён."""


def _parse_support(raw: object) -> SupportConfig | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise BrandConfigError(f"'support' must be an object, got {type(raw).__name__}")
    support_raw: dict[str, Any] = raw
    try:
        slack_raw = support_raw["slack"]
        docs_raw = support_raw["docs"]
        if not isinstance(slack_raw, dict) or not isinstance(docs_raw, dict):
            raise BrandConfigError("support.slack and support.docs must be objects")
        return SupportConfig(
            phone=str(support_raw["phone"]),
            phone_tel=str(support_raw["phoneTel"]),
            email=str(support_raw["email"]),
            slack=SlackSupport(
                channel=str(slack_raw["channel"]),
                workspace=str(slack_raw["workspace"]),
            ),
            docs=DocsSupport(
                url=str(docs_raw["url"]),
                label=str(docs_raw["label"]),
            ),
            compliance_phone=str(support_raw["compliancePhone"]),
        )
    except KeyError as exc:
        raise BrandConfigError(f"missing key in support: {exc}") from exc


def _parse_business_hours(raw: object) -> BusinessHours | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise BrandConfigError(
            f"'businessHours' must be an object, got {type(raw).__name__}"
        )
    hours_raw: dict[str, Any] = raw
    try:
        weekdays_raw = hours_raw["weekdays"]
        if not isinstance(weekdays_raw, dict):
            raise BrandConfigError("businessHours.weekdays must be an object")
        return BusinessHours(
            timezone=str(hours_raw["timezone"]),
            weekdays=WeekdaysHours(
                start=str(weekdays_raw["start"]),
                end=str(weekdays_raw["end"]),
            ),
        )
    except KeyError as exc:
        raise BrandConfigError(f"missing key in businessHours: {exc}") from exc


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
            support=_parse_support(raw.get("support")),
            business_hours=_parse_business_hours(raw.get("businessHours")),
        )
    except KeyError as exc:
        raise BrandConfigError(f"missing key in {path}: {exc}") from exc
