"""Тесты Jinja2-фильтров: форматирование сумм/процентов/дат/severity."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from domain.value_objects.money import Currency, Money
from infrastructure.reports.pdf.template_filters import (
    fmt_date_ru,
    fmt_datetime_ru,
    fmt_inn,
    fmt_pct,
    fmt_pct_share,
    fmt_uzs,
    severity_bg,
    severity_color,
    severity_label,
)

UZS = Currency.UZS
NBSP = " "  # фильтры используют NBSP как разрядный разделитель


# ----- fmt_uzs -----------------------------------------------------------


def test_fmt_uzs_full_with_money() -> None:
    assert fmt_uzs(Money(Decimal("21460000000"), UZS)) == f"21{NBSP}460{NBSP}000{NBSP}000{NBSP}сум"


def test_fmt_uzs_billions_format() -> None:
    assert fmt_uzs(Money(Decimal("21460000000"), UZS), billions=True) == f"21,5{NBSP}млрд{NBSP}сум"


def test_fmt_uzs_zero() -> None:
    assert fmt_uzs(Decimal(0)) == f"0{NBSP}сум"


def test_fmt_uzs_none_returns_dash() -> None:
    assert fmt_uzs(None) == "—"  # em-dash


def test_fmt_uzs_accepts_int() -> None:
    assert fmt_uzs(1500000) == f"1{NBSP}500{NBSP}000{NBSP}сум"


# ----- fmt_pct / fmt_pct_share -------------------------------------------


def test_fmt_pct_converts_decimal_to_percent() -> None:
    assert fmt_pct(Decimal("0.182")) == "18,2%"


def test_fmt_pct_with_sign_positive() -> None:
    assert fmt_pct(Decimal("0.182"), with_sign=True) == "+18,2%"


def test_fmt_pct_with_sign_negative_uses_unicode_minus() -> None:
    assert fmt_pct(Decimal("-0.045"), with_sign=True) == "−4,5%"


def test_fmt_pct_none() -> None:
    assert fmt_pct(None) == "—"


def test_fmt_pct_share_already_in_percent() -> None:
    assert fmt_pct_share(Decimal("22.4")) == "22,4%"


# ----- даты --------------------------------------------------------------


def test_fmt_date_ru_full() -> None:
    # "10 мая 2026"
    assert fmt_date_ru(date(2026, 5, 10)) == "10 мая 2026"


def test_fmt_date_ru_january() -> None:
    # "1 января 2026"
    assert fmt_date_ru(date(2026, 1, 1)) == "1 января 2026"


def test_fmt_datetime_ru_includes_time() -> None:
    expected = "10 мая 2026, 14:05"
    assert fmt_datetime_ru(datetime(2026, 5, 10, 14, 5)) == expected


def test_fmt_date_ru_none() -> None:
    assert fmt_date_ru(None) == "—"


# ----- severity ----------------------------------------------------------


def test_severity_label_localized() -> None:
    # "Высокий" / "Критический"
    assert severity_label("high") == "Высокий"
    assert severity_label("critical") == "Критический"


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
