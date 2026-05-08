"""Jinja2-фильтры для PDF-шаблона.

Регистрируются в ``WeasyPrintPdfRenderer`` при инициализации Environment.
Все фильтры толерантны к ``None`` — на пустых данных возвращают ``"—"``.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from domain.value_objects.money import Money

# NBSP как разрядный разделитель — число "1\xa0500\xa0000" не разорвётся
# при переносе строки. Типографически правильнее ASCII-пробела.
_NBSP = " "

_RU_MONTHS_GENITIVE = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

_RU_MONTHS_SHORT = (
    "янв",
    "фев",
    "мар",
    "апр",
    "мая",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек",
)

_SEVERITY_LABEL = {
    "critical": "Критический",
    "high": "Высокий",
    "medium": "Средний",
    "low": "Низкий",
}

_SEVERITY_COLOR = {
    "critical": "#7A0F0A",
    "high": "#B42318",
    "medium": "#B8730E",
    "low": "#0F8A5F",
}

_SEVERITY_BG = {
    "critical": "#F4D6D2",
    "high": "#FCE8E6",
    "medium": "#FBF1DE",
    "low": "#E6F4EE",
}

# Слово "сум" в Unicode escape — некоторые редакторы любят подменять
# кириллицу копипастом, явные escape-ы дают независимость от пайплайна.
_SUM_WORD = "сум"  # "сум"
_BILLIONS_WORD = "млрд"  # "млрд"
_DASH = "—"  # "—" em-dash
_MINUS = "−"  # "−" Unicode minus


def fmt_uzs(value: Money | Decimal | int | None, *, billions: bool = False) -> str:
    """Форматирует сумму в сумах. ``billions=True`` → "21,5 млрд сум"."""
    if value is None:
        return _DASH
    amount = value.amount if isinstance(value, Money) else Decimal(value)

    if billions:
        billions_value = amount / Decimal("1000000000")
        head = f"{billions_value:.1f}".replace(".", ",")
        return f"{head}{_NBSP}{_BILLIONS_WORD}{_NBSP}{_SUM_WORD}"

    integer = amount.quantize(Decimal("1"))
    return f"{integer:,}".replace(",", _NBSP) + f"{_NBSP}{_SUM_WORD}"


def fmt_uzs_amount_only(value: Money | Decimal | int | None) -> str:
    """Сумма с разрядным разделителем БЕЗ слова «сум».

    Используется в шаблоне когда «сум» рендерится отдельным текстом
    (cover decision-meta) или в табличной колонке с подписью «Суммы в сумах»
    в footer'е (Phase 10). На ``None`` → "—".
    """
    if value is None:
        return _DASH
    amount = value.amount if isinstance(value, Money) else Decimal(value)
    integer = amount.quantize(Decimal("1"))
    return f"{integer:,}".replace(",", _NBSP)


def fmt_pct(value: Decimal | None, *, with_sign: bool = False, decimals: int = 1) -> str:
    """Форматирует число как проценты. Принимает значение **уже в процентах**.

    CA-043: ``Decimal("18.2")`` → ``"18,2%"`` (не fraction). Это контракт всего
    стека — ``kpi_calculator`` производит ``yoy_pct = (a - b) / b * 100``,
    frontend ``formatYoy(-14.4) → "−14,4%"``, ``revenue_drop_yoy_50`` пишет
    evidence как percent. Прежнее ``* 100`` внутри фильтра удваивало масштаб
    (PDF показывал ``−1442,9%`` вместо ``−14,4%``).
    """
    if value is None:
        return _DASH
    pct = Decimal(value)
    sign = ""
    if with_sign:
        if pct > 0:
            sign = "+"
        elif pct < 0:
            sign = _MINUS
            pct = -pct
    formatted = f"{pct:.{decimals}f}".replace(".", ",")
    return f"{sign}{formatted}%"


def fmt_pct_share(value: Decimal | None, *, decimals: int = 1) -> str:
    """Доля в процентах 0..100 (как ``CounterpartyShare.share_pct``).

    Не умножает на 100 — значения уже в нужной шкале.
    """
    if value is None:
        return _DASH
    formatted = f"{Decimal(value):.{decimals}f}".replace(".", ",")
    return f"{formatted}%"


def fmt_date_ru(value: date | datetime | None) -> str:
    """``date(2026, 5, 10)`` → "10 мая 2026"."""
    if value is None:
        return _DASH
    d = value.date() if isinstance(value, datetime) else value
    month = _RU_MONTHS_GENITIVE[d.month - 1]
    return f"{d.day} {month} {d.year}"


def fmt_datetime_ru(value: datetime | None) -> str:
    """``datetime(2026, 5, 10, 14, 32)`` → "10 мая 2026, 14:32"."""
    if value is None:
        return _DASH
    return f"{fmt_date_ru(value.date())}, {value.hour:02d}:{value.minute:02d}"


def fmt_date_ru_short(value: date | datetime | None) -> str:
    """``date(2026, 4, 30)`` → "30 апр 2026". Для running head банковской шапки."""
    if value is None:
        return _DASH
    d = value.date() if isinstance(value, datetime) else value
    month = _RU_MONTHS_SHORT[d.month - 1]
    return f"{d.day} {month} {d.year}"


def fmt_date_ru_month(value: date | datetime | None) -> str:
    """``date(2018, 3, 14)`` → "марта 2018". Для stat-tile «с марта 2018»."""
    if value is None:
        return _DASH
    d = value.date() if isinstance(value, datetime) else value
    month = _RU_MONTHS_GENITIVE[d.month - 1]
    return f"{month} {d.year}"


def severity_label(value: str | None) -> str:
    if value is None:
        return _DASH
    return _SEVERITY_LABEL.get(value.lower(), value.capitalize())


def severity_color(value: str | None) -> str:
    if value is None:
        return "#5A6478"
    return _SEVERITY_COLOR.get(value.lower(), "#5A6478")


def severity_bg(value: str | None) -> str:
    if value is None:
        return "#F1F5F9"
    return _SEVERITY_BG.get(value.lower(), "#F1F5F9")


def fmt_inn(value: str | None) -> str:
    """ИНН с разрядным разделителем: "306399449" → "306\xa0399\xa0449"."""
    if not value:
        return _DASH
    digits = value.strip()
    chunks: list[str] = []
    while digits:
        chunks.insert(0, digits[-3:])
        digits = digits[:-3]
    return _NBSP.join(chunks)
