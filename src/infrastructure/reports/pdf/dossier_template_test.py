"""Smoke-тест Jinja2-шаблона досье.

Не запускает WeasyPrint — только Jinja-render. Проверяем, что:
* шаблон загружается без syntax errors;
* контекст с минимальным набором переменных рендерится;
* в HTML присутствуют ключевые куски (имя заёмщика, ИНН, секции A–G).

Полный smoke с PDF-байтами — в ``pdf_renderer_test.py`` (Phase 3.C.4).
"""

from __future__ import annotations

import base64
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import jinja2

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

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _make_env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    env.filters["fmt_uzs"] = fmt_uzs
    env.filters["fmt_pct"] = fmt_pct
    env.filters["fmt_pct_share"] = fmt_pct_share
    env.filters["fmt_date_ru"] = fmt_date_ru
    env.filters["fmt_datetime_ru"] = fmt_datetime_ru
    env.filters["fmt_inn"] = fmt_inn
    env.filters["severity_label"] = severity_label
    env.filters["severity_color"] = severity_color
    env.filters["severity_bg"] = severity_bg
    return env


class _Stub:
    def __init__(self, **kw: object) -> None:
        self.__dict__.update(kw)


def _minimal_context() -> dict[str, object]:
    fake_png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32).decode("ascii")
    return {
        "application_id": "BR-2026-0F8A",
        "generated_at": datetime(2026, 5, 10, 14, 32),
        "status_label": "На рассмотрении",
        "borrower": _Stub(
            name="ООО «Полярная Звезда»",
            inn=_Stub(value="306399449"),
            registration_date=date(2018, 3, 14),
            director_name="Каримов Шохрух",
            director_appointed_at=date(2018, 3, 14),
            okved_main="46.39",
            registered_address="г. Ташкент",
        ),
        "snapshot": _Stub(as_of=date(2026, 4, 30)),
        "loan_request": _Stub(
            amount=Money(Decimal("800000000"), Currency.UZS),
            term_months=24,
            rate_pct=Decimal("22.5"),
        ),
        "rules_version": "v1.uz-msb",
        "rules_evaluated": 17,
        "display_score": 73,
        "gauge_angle_deg": 41.4,
        "recommendation": "review",
        "recommendation_label": "К пересмотру",
        "red_flags_count_label": "4 high·medium·low",
        "legal_form_label": "ООО",
        "annual_reports": [
            _Stub(
                period=_Stub(start=date(2023, 1, 1)),
                revenue=Money(Decimal("14820000000"), Currency.UZS),
                net_profit=Money(Decimal("1185000000"), Currency.UZS),
                taxes_paid=Money(Decimal("237000000"), Currency.UZS),
            ),
            _Stub(
                period=_Stub(start=date(2024, 1, 1)),
                revenue=Money(Decimal("17640000000"), Currency.UZS),
                net_profit=Money(Decimal("1590000000"), Currency.UZS),
                taxes_paid=Money(Decimal("318000000"), Currency.UZS),
            ),
        ],
        "kpi_slots": [
            {
                "label": "Revenue LTM",
                "value": "21,5 млрд",
                "yoy_pct": Decimal("18.2"),
                "yoy_positive": True,
                "yoy_label": "+18,2%",
            },
            {
                "label": "EBITDA",
                "value": None,
                "yoy_pct": None,
                "yoy_positive": False,
                "yoy_label": "",
            },
        ],
        "chart_revenue_24m_b64": fake_png,
        "top_buyers": [
            _Stub(
                name="ООО «Самарканд Маркет»",
                share_pct=Decimal("22.4"),
                is_new=False,
                months_since_registration=72,
            ),
        ],
        "top_suppliers": [
            _Stub(
                name="ООО «Узбек»",
                share_pct=Decimal("38.7"),
                is_new=False,
                months_since_registration=60,
            ),
        ],
        "tax_summary": _Stub(
            delays=[],
            max_delay_days=0,
            penalties_total=None,
            account_freezes_count_12m=0,
            has_freezes_12m=False,
        ),
        "red_flags": [
            _Stub(
                rule_id="SUPPLIER_CONCENTRATION_30",
                name="Концентрация",
                description="Топ-1: 38,7%",
                severity="high",
                source="Basel III concentration risk",
                evidence_value="38,7%",
                evidence_label="Доля топ-1",
            ),
        ],
    }


def test_template_renders_minimal_context() -> None:
    env = _make_env()
    tpl = env.get_template("dossier.html")
    html = tpl.render(**_minimal_context())

    assert "<!doctype html>" in html
    assert "Credit Assistant" in html
    assert "BR-2026-0F8A" in html
    # ИНН: разрядный разделитель — NBSP
    assert "306 399 449" in html
    # Секции A–G по русским заголовкам
    assert "G. Сводная" in html
    assert "A. Идентификация" in html
    assert "B. Финансовые" in html
    assert "C. Динамика" in html
    assert "D. Контрагенты" in html
    assert "E. Налоговая" in html
    assert "F. Сработавшие" in html
    # Gauge + recommendation
    assert "73" in html
    assert "К пересмотру" in html
    # CA-025: arc endpoints должны лежать на окружности r=90 вокруг (100, 110),
    # иначе WeasyPrint рисует кривые мимо секторов. Проверяем оба «промежуточных»
    # узла (cos/sin 45° * 90 ≈ 63.64) и крайние точки (10/190 на горизонтали).
    assert 'd="M 10 110 A 90 90 0 0 1 36.36 46.36"' in html
    assert 'd="M 36.36 46.36 A 90 90 0 0 1 100 20"' in html
    assert 'd="M 100 20 A 90 90 0 0 1 163.64 46.36"' in html
    assert 'd="M 163.64 46.36 A 90 90 0 0 1 190 110"' in html
    # Red flag rendered
    assert "SUPPLIER_CONCENTRATION_30" in html
    # KPI: Revenue LTM активный, EBITDA пустой — оба в разметке
    assert "Revenue LTM" in html
    assert "Нет данных для расчёта" in html


def test_template_handles_empty_red_flags() -> None:
    env = _make_env()
    tpl = env.get_template("dossier.html")
    ctx = _minimal_context()
    ctx["red_flags"] = []
    html = tpl.render(**ctx)

    assert "Сигналы не сработали" in html


def test_template_handles_missing_loan_request() -> None:
    env = _make_env()
    tpl = env.get_template("dossier.html")
    ctx = _minimal_context()
    ctx["loan_request"] = None
    html = tpl.render(**ctx)

    assert "BR-2026-0F8A" in html
    assert "Запрос:" not in html
