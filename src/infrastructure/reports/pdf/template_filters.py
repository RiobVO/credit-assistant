"""Jinja2-фильтры для PDF-шаблона.

T0.4 / ADR-0015: фильтры строятся per-render через closure'ы поверх
``PdfMessages`` — currency suffix, месяцы, severity labels резолвятся
из i18n JSON, не из module-level RU-констант. Closure-инжект сделан
через ``make_filter_*`` фабрики, регистрируемые в
``WeasyPrintPdfRenderer.render`` при каждом вызове (overhead — микросекунды).

Все фильтры толерантны к ``None`` — на пустых данных возвращают ``"—"``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal

from application.dto.pdf_messages import PdfMessages
from domain.value_objects.money import Money

# NBSP как разрядный разделитель — число "1\xa0500\xa0000" не разорвётся
# при переносе строки. Типографически правильнее ASCII-пробела.
_NBSP = " "
_DASH = "—"  # em-dash
_MINUS = "−"  # Unicode minus

# Severity палитра остаётся module-level — это design tokens (CSS-цвета),
# не локализуемый контент.
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


# --- closure factories ----------------------------------------------------


def make_fmt_uzs(messages: PdfMessages) -> Callable[..., str]:
    """Создаёт ``fmt_uzs`` filter: «21,5 млрд сум» / «21.5 mlrd soʻm»."""
    billion_word = messages.currency_billion_short
    sum_word = messages.cover_loan_request_uzs_suffix

    def _fmt_uzs(value: Money | Decimal | int | None, *, billions: bool = False) -> str:
        if value is None:
            return _DASH
        amount = value.amount if isinstance(value, Money) else Decimal(value)
        if billions:
            billions_value = amount / Decimal("1000000000")
            head = f"{billions_value:.1f}".replace(".", ",")
            return f"{head}{_NBSP}{billion_word}{_NBSP}{sum_word}"
        integer = amount.quantize(Decimal("1"))
        return f"{integer:,}".replace(",", _NBSP) + f"{_NBSP}{sum_word}"

    return _fmt_uzs


def fmt_uzs_amount_only(value: Money | Decimal | int | None) -> str:
    """Сумма с разрядным разделителем БЕЗ слова «сум».

    Используется в шаблоне, когда «сум»/«soʻm» рендерится отдельным текстом
    (cover decision-meta) или в табличной колонке с подписью «Суммы в сумах»
    в footer'е. На ``None`` → "—". Не зависит от локали.
    """
    if value is None:
        return _DASH
    amount = value.amount if isinstance(value, Money) else Decimal(value)
    integer = amount.quantize(Decimal("1"))
    return f"{integer:,}".replace(",", _NBSP)


def fmt_pct(value: Decimal | None, *, with_sign: bool = False, decimals: int = 1) -> str:
    """Форматирует число как проценты. Принимает значение **уже в процентах**.

    CA-043: ``Decimal("18.2")`` → ``"18,2%"`` (не fraction). Не зависит от локали.
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
    """Доля в процентах 0..100 (как ``CounterpartyShare.share_pct``)."""
    if value is None:
        return _DASH
    formatted = f"{Decimal(value):.{decimals}f}".replace(".", ",")
    return f"{formatted}%"


def make_fmt_date(messages: PdfMessages) -> Callable[[date | datetime | None], str]:
    """RU: ``date(2026,5,10) → "10 мая 2026"``. UZ: ``"10 may 2026"``."""
    months = messages.month_full

    def _fmt_date(value: date | datetime | None) -> str:
        if value is None:
            return _DASH
        d = value.date() if isinstance(value, datetime) else value
        return f"{d.day} {months[d.month - 1]} {d.year}"

    return _fmt_date


def make_fmt_datetime(messages: PdfMessages) -> Callable[[datetime | None], str]:
    """``datetime(2026,5,10,14,32) → "10 мая 2026, 14:32"``."""
    fmt_date = make_fmt_date(messages)

    def _fmt_datetime(value: datetime | None) -> str:
        if value is None:
            return _DASH
        return f"{fmt_date(value.date())}, {value.hour:02d}:{value.minute:02d}"

    return _fmt_datetime


def make_fmt_date_short(messages: PdfMessages) -> Callable[[date | datetime | None], str]:
    """``date(2026,4,30) → "30 апр 2026"`` / ``"30 apr 2026"``."""
    months = messages.month_short

    def _fmt_date_short(value: date | datetime | None) -> str:
        if value is None:
            return _DASH
        d = value.date() if isinstance(value, datetime) else value
        return f"{d.day} {months[d.month - 1]} {d.year}"

    return _fmt_date_short


def make_fmt_date_month(messages: PdfMessages) -> Callable[[date | datetime | None], str]:
    """``date(2018,3,14) → "марта 2018"`` / ``"mart 2018"`` — для stat-tile."""
    months = messages.month_full

    def _fmt_date_month(value: date | datetime | None) -> str:
        if value is None:
            return _DASH
        d = value.date() if isinstance(value, datetime) else value
        return f"{months[d.month - 1]} {d.year}"

    return _fmt_date_month


def make_severity_label(messages: PdfMessages) -> Callable[[str | None], str]:
    """RU: ``"critical" → "Критический"``; UZ: ``"Kritik"``."""

    def _severity_label(value: str | None) -> str:
        if value is None:
            return _DASH
        return messages.severity.get(value.lower(), value.capitalize())

    return _severity_label


def severity_color(value: str | None) -> str:
    if value is None:
        return "#5A6478"
    return _SEVERITY_COLOR.get(value.lower(), "#5A6478")


def severity_bg(value: str | None) -> str:
    if value is None:
        return "#F1F5F9"
    return _SEVERITY_BG.get(value.lower(), "#F1F5F9")


def fmt_inn(value: str | None) -> str:
    """ИНН с разрядным разделителем: "306399449" → "306 399 449"."""
    if not value:
        return _DASH
    digits = value.strip()
    chunks: list[str] = []
    while digits:
        chunks.insert(0, digits[-3:])
        digits = digits[:-3]
    return _NBSP.join(chunks)
