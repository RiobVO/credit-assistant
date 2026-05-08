"""BrandConfig DTO: tenant-brand параметры досье (имя банка, primary-цвет и т.п.).

Чистый dataclass без I/O. Загрузка из ``config/brands/<id>.json`` живёт в
``infrastructure.brand.brand_config.load_brand``. Этот модуль — типизированный
контракт, через который application/infrastructure обмениваются brand-данными
без рассинхрона со стеком фронтенда (CA-066 / ADR-0011).

Field naming: snake_case (Python-конвенция), JSON-ключи camelCase
(``logoMark``, ``primaryHover``, ...) — маппинг делается в loader'е.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrandConfig:
    id: str
    name: str
    tagline: str
    logo_mark: str
    primary: str
    primary_hover: str
    primary_soft: str
    primary_ink: str
    primary_ring: str
