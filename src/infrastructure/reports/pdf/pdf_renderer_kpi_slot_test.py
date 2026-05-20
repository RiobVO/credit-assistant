"""Unit-тесты `_kpi_slot` (CA-048 — level_tone в PDF-контексте).

Существующий `pdf_renderer_test.py` skip'ается на Windows (нужен GTK runtime
для WeasyPrint). Здесь — pure-Python тесты на helper, который превращает
``KpiValue`` в dict для Jinja-шаблона: безопасны на любом host'е и
гарантируют, что новый ключ ``level_tone`` попадает в dict (а CSS-класс
``.kpi.lvl-{level_tone}`` в шаблоне опирается ровно на этот ключ).
"""

from __future__ import annotations

from decimal import Decimal

from application.dto.kpi_bundle import KpiLevelTone, KpiUnit, KpiValue
from infrastructure.i18n.pdf_messages import load_pdf_messages
from infrastructure.reports.pdf.pdf_renderer import _kpi_slot
from infrastructure.reports.pdf.template_filters import make_fmt_uzs

_RU = load_pdf_messages("ru")
_FMT_UZS = make_fmt_uzs(_RU)


def test_kpi_slot_includes_level_tone_warn() -> None:
    """ROE 10.7% → level_tone "warn" → CSS class .kpi.lvl-warn в шаблоне."""
    kpi = KpiValue(
        value=Decimal("10.7"),
        unit=KpiUnit.PCT,
        yoy_pct=None,
        sparkline=(),
        level_tone=KpiLevelTone.WARN,
    )
    slot = _kpi_slot("roe", kpi, _RU, _FMT_UZS)
    assert slot["level_tone"] == "warn"


def test_kpi_slot_includes_level_tone_good() -> None:
    kpi = KpiValue(
        value=Decimal("0"),
        unit=KpiUnit.RATIO,
        yoy_pct=None,
        sparkline=(),
        level_tone=KpiLevelTone.GOOD,
    )
    slot = _kpi_slot("debt_to_ebit", kpi, _RU, _FMT_UZS)
    assert slot["level_tone"] == "good"


def test_kpi_slot_includes_level_tone_bad() -> None:
    kpi = KpiValue(
        value=Decimal("5.80"),
        unit=KpiUnit.RATIO,
        yoy_pct=None,
        sparkline=(),
        level_tone=KpiLevelTone.BAD,
    )
    slot = _kpi_slot("debt_to_ebit", kpi, _RU, _FMT_UZS)
    assert slot["level_tone"] == "bad"


def test_kpi_slot_no_level_tone_for_revenue_ltm() -> None:
    """KPI без universal threshold (revenue_ltm) — level_tone остаётся None,
    шаблон не добавит класс .lvl-*."""
    kpi = KpiValue(
        value=Decimal("21460000000"),
        unit=KpiUnit.UZS,
        yoy_pct=Decimal("18.2"),
        sparkline=(),
    )
    slot = _kpi_slot("revenue_ltm", kpi, _RU, _FMT_UZS)
    assert slot["level_tone"] is None


def test_kpi_slot_none_kpi_returns_level_tone_none() -> None:
    """Empty KPI (degraded mode) — level_tone None, чтобы шаблон не упал
    при `{% if slot.level_tone %}`."""
    slot = _kpi_slot("ebit", None, _RU, _FMT_UZS)
    assert slot["level_tone"] is None


# ----------- ADR-0024 (Session 1): расширенный KPI набор ---------------------
#
# Проверяем что новые kpi_label entries резолвятся для обеих локалей
# и slot dict-форма не падает.


_UZ = load_pdf_messages("uz")
_FMT_UZS_UZ = make_fmt_uzs(_UZ)


def test_kpi_slot_ebitda_label_resolves_ru() -> None:
    kpi = KpiValue(value=Decimal("200000000"), unit=KpiUnit.UZS, yoy_pct=None, sparkline=())
    slot = _kpi_slot("ebitda", kpi, _RU, _FMT_UZS)
    assert slot["label"] == "EBITDA"


def test_kpi_slot_current_ratio_label_resolves_uz() -> None:
    kpi = KpiValue(
        value=Decimal("1.8"),
        unit=KpiUnit.RATIO,
        yoy_pct=None,
        sparkline=(),
        level_tone=KpiLevelTone.GOOD,
    )
    slot = _kpi_slot("current_ratio", kpi, _UZ, _FMT_UZS_UZ)
    assert slot["label"] == "Joriy likvidlik"
    assert slot["level_tone"] == "good"


def test_kpi_slot_dscr_ru_label() -> None:
    kpi = KpiValue(value=Decimal("1.25"), unit=KpiUnit.RATIO, yoy_pct=None, sparkline=())
    slot = _kpi_slot("dscr", kpi, _RU, _FMT_UZS)
    assert slot["label"] == "DSCR"


def test_kpi_slot_working_capital_ru_label_uzs_value() -> None:
    """Working Capital — UZS Money; fmt_uzs форматирует с billions=True."""
    kpi = KpiValue(value=Decimal("2000000000"), unit=KpiUnit.UZS, yoy_pct=None, sparkline=())
    slot = _kpi_slot("working_capital", kpi, _RU, _FMT_UZS)
    assert slot["label"] == "Оборотный капитал"
    # 2 млрд → fmt_uzs ставит «2,0 млрд сум» или подобное; деталь форматирования
    # покрыта другим тестом template_filters, тут проверяем тип и непустоту.
    assert isinstance(slot["value"], str)
    assert slot["value"] != "—"
