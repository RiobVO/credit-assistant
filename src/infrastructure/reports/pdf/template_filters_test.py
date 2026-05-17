"""Тесты Jinja2-фильтров: форматирование сумм/процентов/дат/severity.

T0.4 / ADR-0015: локализованные filters (fmt_uzs / fmt_date / severity_label)
строятся через ``make_*`` factories поверх PdfMessages. Тесты загружают
ru.json через ``load_pdf_messages("ru")`` и проверяют RU-вывод; UZ-вывод
проверяется отдельным тест-классом ``TestUzLocale``.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from domain.value_objects.money import Currency, Money
from infrastructure.i18n.pdf_messages import load_pdf_messages
from infrastructure.reports.pdf.template_filters import (
    fmt_inn,
    fmt_pct,
    fmt_pct_share,
    make_fmt_date,
    make_fmt_datetime,
    make_fmt_uzs,
    make_severity_label,
    severity_bg,
    severity_color,
)

UZS = Currency.UZS
NBSP = " "  # фильтры используют NBSP как разрядный разделитель

_RU = load_pdf_messages("ru")
_UZ = load_pdf_messages("uz")

fmt_uzs_ru = make_fmt_uzs(_RU)
fmt_date_ru = make_fmt_date(_RU)
fmt_datetime_ru = make_fmt_datetime(_RU)
severity_label_ru = make_severity_label(_RU)


# ----- fmt_uzs -----------------------------------------------------------


def test_fmt_uzs_full_with_money() -> None:
    assert fmt_uzs_ru(Money(Decimal("21460000000"), UZS)) == (
        f"21{NBSP}460{NBSP}000{NBSP}000{NBSP}сум"
    )


def test_fmt_uzs_billions_format() -> None:
    assert fmt_uzs_ru(Money(Decimal("21460000000"), UZS), billions=True) == (
        f"21,5{NBSP}млрд{NBSP}сум"
    )


def test_fmt_uzs_zero() -> None:
    assert fmt_uzs_ru(Decimal(0)) == f"0{NBSP}сум"


def test_fmt_uzs_none_returns_dash() -> None:
    assert fmt_uzs_ru(None) == "—"


def test_fmt_uzs_accepts_int() -> None:
    assert fmt_uzs_ru(1500000) == f"1{NBSP}500{NBSP}000{NBSP}сум"


# ----- fmt_pct / fmt_pct_share -------------------------------------------


def test_fmt_pct_formats_percent_value() -> None:
    """CA-043: fmt_pct принимает значение уже в процентах, не fraction."""
    assert fmt_pct(Decimal("18.2")) == "18,2%"


def test_fmt_pct_with_sign_positive() -> None:
    assert fmt_pct(Decimal("18.2"), with_sign=True) == "+18,2%"


def test_fmt_pct_with_sign_negative_uses_unicode_minus() -> None:
    assert fmt_pct(Decimal("-14.4"), with_sign=True) == "−14,4%"


def test_fmt_pct_none() -> None:
    assert fmt_pct(None) == "—"


def test_fmt_pct_does_not_double_scale_percent_input() -> None:
    """Regression-guard: CA-043. fmt_pct не умножает на 100."""
    assert fmt_pct(Decimal("-14.4"), with_sign=True) == "−14,4%"


def test_fmt_pct_share_already_in_percent() -> None:
    assert fmt_pct_share(Decimal("22.4")) == "22,4%"


# ----- даты --------------------------------------------------------------


def test_fmt_date_ru_full() -> None:
    assert fmt_date_ru(date(2026, 5, 10)) == "10 мая 2026"


def test_fmt_date_ru_january() -> None:
    assert fmt_date_ru(date(2026, 1, 1)) == "1 января 2026"


def test_fmt_datetime_ru_includes_time() -> None:
    expected = "10 мая 2026, 14:05"
    assert fmt_datetime_ru(datetime(2026, 5, 10, 14, 5)) == expected


def test_fmt_date_ru_none() -> None:
    assert fmt_date_ru(None) == "—"


# ----- severity ----------------------------------------------------------


def test_severity_label_localized() -> None:
    assert severity_label_ru("high") == "Высокий"
    assert severity_label_ru("critical") == "Критический"


def test_severity_color_known() -> None:
    assert severity_color("high") == "#B42318"
    assert severity_color("low") == "#0F8A5F"


def test_severity_color_unknown_falls_back() -> None:
    assert severity_color("unknown_severity") == "#5A6478"


def test_severity_bg_known() -> None:
    assert severity_bg("medium") == "#FBF1DE"


# ----- ИНН ---------------------------------------------------------------


def test_fmt_inn_groups_by_three() -> None:
    assert fmt_inn("306399449") == f"306{NBSP}399{NBSP}449"


def test_fmt_inn_pinfl_14_digits() -> None:
    assert fmt_inn("12345678901234") == f"12{NBSP}345{NBSP}678{NBSP}901{NBSP}234"


def test_fmt_inn_empty() -> None:
    assert fmt_inn("") == "—"
    assert fmt_inn(None) == "—"


# ----- UZ локаль ---------------------------------------------------------


class TestUzLocale:
    """T0.4: closure-инжект локали через PdfMessages."""

    def test_fmt_uzs_billions_uses_uz_units(self) -> None:
        fmt_uzs_uz = make_fmt_uzs(_UZ)
        assert fmt_uzs_uz(Money(Decimal("21460000000"), UZS), billions=True) == (
            f"21,5{NBSP}mlrd{NBSP}soʻm"
        )

    def test_fmt_date_uses_uz_month(self) -> None:
        fmt_date_uz = make_fmt_date(_UZ)
        assert fmt_date_uz(date(2026, 5, 10)) == "10 may 2026"

    def test_severity_label_uses_uz_word(self) -> None:
        severity_label_uz = make_severity_label(_UZ)
        assert severity_label_uz("critical") == "Kritik"
        assert severity_label_uz("high") == "Yuqori"
