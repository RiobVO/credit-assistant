"""BrandConfig DTO: tenant-brand параметры досье (имя банка, primary-цвет и т.п.).

Чистый dataclass без I/O. Загрузка из ``config/brands/<id>.json`` живёт в
``infrastructure.brand.brand_config.load_brand``. Этот модуль — типизированный
контракт, через который application/infrastructure обмениваются brand-данными
без рассинхрона со стеком фронтенда (CA-066 / ADR-0011).

Field naming: snake_case (Python-конвенция), JSON-ключи camelCase
(``logoMark``, ``primaryHover``, ...) — маппинг делается в loader'е.

CA-DS6/7/8: support (контакты для /help) и business_hours (расписание
hotline) — опциональные секции. PDF их не использует; только frontend
HelpView. None если секция отсутствует.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SlackSupport:
    channel: str
    workspace: str


@dataclass(frozen=True, slots=True)
class DocsSupport:
    url: str
    label: str


@dataclass(frozen=True, slots=True)
class SupportConfig:
    """Контакты поддержки для /help (CA-DS6 + CA-DS8).

    ``phone`` — display-форма (``"+998 71 200-00-00"``), ``phone_tel`` —
    ``tel:``-URL (``"tel:+998712000000"``). Compliance phone (CA-DS8) —
    отдельный канал для регуляторных вопросов; обычный analyst-support
    не использует его.
    """

    phone: str
    phone_tel: str
    email: str
    slack: SlackSupport
    docs: DocsSupport
    compliance_phone: str


@dataclass(frozen=True, slots=True)
class WeekdaysHours:
    start: str  # ``"09:00"``
    end: str  # ``"18:00"``


@dataclass(frozen=True, slots=True)
class BusinessHours:
    """Расписание hotline (CA-DS7).

    ``timezone`` — IANA-имя (``"Asia/Tashkent"``). ``weekdays`` — окно для
    пн-пт; выходные считаются закрытыми. Lunch-break сейчас не моделируем
    (open/closed достаточно для smoke; lunch — следующий шаг при запросе).
    """

    timezone: str
    weekdays: WeekdaysHours


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
    # CA-DS6/7/8: default=None — обратная совместимость с существующими
    # call-sites (PDF templates / use-case тесты), которые конструируют
    # BrandConfig без новых секций.
    support: SupportConfig | None = None
    business_hours: BusinessHours | None = None
    # T0.4 / ADR-0015: per-tenant дефолтная локаль PDF-досье. ``None`` →
    # fallback на "ru". ``uzbekbank`` brand-tenant получает "uz" — UZ-демо.
    default_lang: str | None = None
