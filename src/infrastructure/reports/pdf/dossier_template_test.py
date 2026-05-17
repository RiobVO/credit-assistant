"""Smoke-тест Jinja2-шаблона досье (Phase 10 design statement).

Не запускает WeasyPrint — только Jinja-render. Проверяем, что:
* шаблон загружается без syntax errors;
* контекст с минимальным набором переменных рендерится;
* в HTML присутствуют ключевые куски (hero, stat tiles, observations,
  brand-name, секции A–F);
* «✓ Проверено в ГНК» pill отсутствует физически (Phase 9 lesson, mock UI
  на decision-screens опаснее чем на форме-ввода);
* F-секция рендерит human-readable name (не rule_id) в title.

Полный smoke с PDF-байтами — в ``pdf_renderer_test.py``.
"""

from __future__ import annotations

import base64
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import jinja2

from application.dto.brand_config import BrandConfig
from application.services.observations_builder import Observation, Observations
from domain.value_objects.money import Currency, Money
from infrastructure.reports.pdf.template_filters import (
    fmt_date_ru,
    fmt_date_ru_month,
    fmt_date_ru_short,
    fmt_datetime_ru,
    fmt_inn,
    fmt_pct,
    fmt_pct_share,
    fmt_uzs,
    fmt_uzs_amount_only,
    severity_bg,
    severity_color,
    severity_label,
)

TEMPLATES_DIR = Path(__file__).parent / "templates"
NBSP = " "  # фильтры используют NBSP как разрядный разделитель


def _make_env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    env.filters["fmt_uzs"] = fmt_uzs
    env.filters["fmt_uzs_amount_only"] = fmt_uzs_amount_only
    env.filters["fmt_pct"] = fmt_pct
    env.filters["fmt_pct_share"] = fmt_pct_share
    env.filters["fmt_date_ru"] = fmt_date_ru
    env.filters["fmt_date_ru_short"] = fmt_date_ru_short
    env.filters["fmt_date_ru_month"] = fmt_date_ru_month
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
        "brand": BrandConfig(
            id="uzbekbank",
            name="Uzbekbank Credit",
            tagline="Bank Mode · Андижон",
            logo_mark="UB",
            primary="#CC785C",
            primary_hover="#B5624A",
            primary_soft="#F7E8DF",
            primary_ink="#6E2F1C",
            primary_ring="rgba(204,120,92,0.22)",
        ),
        "application_id": "BR-2026-0F8A",
        "generated_at": datetime(2026, 5, 10, 14, 32),
        "borrower": _Stub(
            name="ООО «Полярная Звезда»",
            inn=_Stub(value="306399449"),
            registration_date=date(2018, 3, 14),
            director_name="Каримов Шохрух",
            director_appointed_at=date(2018, 3, 14),
            okved_main="46.39",
            registered_address="г. Ташкент, Юнусабадский р-н",
        ),
        "borrower_initials": "ПЗ",
        "snapshot": _Stub(as_of=date(2026, 4, 30)),
        "loan_request": _Stub(
            amount=Money(Decimal("800000000"), Currency.UZS),
            term_months=24,
            rate_pct=Decimal("22.5"),
        ),
        "rules_version": "v1.uz-msb",
        "rules_evaluated": 17,
        "display_score": 73,
        "gauge_angle_deg": "41.40",
        "recommendation": "review",
        "recommendation_label": "К пересмотру",
        "signal_breakdown": [
            {"severity": "high", "label": "1 высокий", "count": 1},
            {"severity": "medium", "label": "2 средних", "count": 2},
            {"severity": "low", "label": "1 низкий", "count": 1},
        ],
        "legal_form_label": "Общество с ограниченной ответственностью",
        "legal_form_short": "ООО",
        "business_age_years": 8,
        "business_age_unit": "лет",
        "region_city": "Ташкент",
        "region_district": "Юнусабадский район",
        "okved_short_label": "Опт. торговля пищ. продуктами",
        "okved_full_label": "Неспециализированная оптовая торговля пищевыми продуктами",
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
                "level_tone": "good",
            },
            {
                "label": "EBITDA",
                "value": None,
                "yoy_pct": None,
                "yoy_positive": False,
                "yoy_label": "",
                "level_tone": None,
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
                name="ООО «Узбек Поставщик»",
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
            {
                "rule_id": "SUPPLIER_CONCENTRATION_30",
                "name": "Концентрация поставщика >60% закупок",
                "description": "Топ-1: 38,7%",
                "severity": "high",
                "severity_label": "Высокий",
                "source": "Basel III concentration risk",
                "evidence_value": "38,7%",
                "evidence_label": "Доля топ-1",
            }
        ],
        "observations": Observations(
            strengths=(
                Observation(
                    head="Рост выручки +18,2% YoY",
                    num="+18,2%",
                    ctx="3 года подряд",
                ),
            ),
            risks=(
                Observation(
                    head="Концентрация поставщика >60% закупок",
                    num="38,7",
                    ctx="ООО «Узбек Поставщик»",
                ),
            ),
        ),
    }


def test_template_renders_minimal_context() -> None:
    env = _make_env()
    tpl = env.get_template("dossier.html")
    html = tpl.render(**_minimal_context())

    assert "<!doctype html>" in html
    assert "Uzbekbank Credit" in html
    assert "BR-2026-0F8A" in html
    # ИНН: разрядный разделитель — NBSP
    assert "306\xa0399\xa0449" in html
    # Cover hero
    assert "Кредитный меморандум" in html
    assert "ООО «Полярная Звезда»" in html
    # Decision recommendation
    assert "К пересмотру" in html
    assert "73" in html
    # Signal breakdown inline
    assert "1 высокий" in html
    assert "2 средних" in html
    # Observations block
    assert "Ключевые наблюдения" in html
    assert "Сильные стороны" in html
    assert "Зоны риска" in html
    assert "Рост выручки +18,2% YoY" in html
    # Section A — hero + stat tiles
    assert "A. Идентификация" not in html, "Phase 10: sec-tag отдельный от h2"
    assert ">A<" in html, "sec-tag «A» рендерится"
    assert "Идентификация заёмщика" in html
    assert "ПЗ" in html, "borrower initials в id-avatar"
    assert "В бизнесе" in html  # stat-tile label
    assert "Ташкент" in html  # region city
    assert "Юнусабадский район" in html
    assert "Опт. торговля пищ. продуктами" in html  # okved short
    # Section B — financial table
    assert "Финансовые показатели" in html
    # Section C — chart
    assert "Динамика помесячной выручки" in html
    # Section D — counterparties
    assert "Топ контрагентов" in html
    # Section E — tax
    assert "Налоговая дисциплина" in html
    # Section F — human-readable rule name (не rule_id в title). HTML
    # autoescape конвертирует «>» в &gt; — проверяем prefix без &gt;.
    assert "Концентрация поставщика" in html
    assert "SUPPLIER_CONCENTRATION_30" in html  # rule_id в .src строке
    # Score gauge SVG arcs
    assert 'd="M 10 110 A 90 90 0 0 1 36.36 46.36"' in html


def test_template_excludes_gnk_verified_pill() -> None:
    """Phase 9 lesson: mock «✓ Проверено в ГНК» pill убран физически.

    Pill дезинформирует compliance-офицера, который читает PDF как
    decision-document. См. memory ``feedback_mock_ui_on_decision_screens.md``.
    """
    env = _make_env()
    tpl = env.get_template("dossier.html")
    html = tpl.render(**_minimal_context())

    assert "Проверено в ГНК" not in html
    assert "pill-ok" not in html


def test_template_renders_gnk_certificate_row_when_provided() -> None:
    """T0.3.2: если в context есть gnk_certificate — Section A добавляет row
    со статусом + источником. Без gnk_certificate — row отсутствует."""
    env = _make_env()
    tpl = env.get_template("dossier.html")

    # Без справки — row отсутствует.
    ctx_no_cert = _minimal_context()
    ctx_no_cert.setdefault("gnk_certificate", None)
    html_no_cert = tpl.render(**ctx_no_cert)
    assert "Справка ГНК" not in html_no_cert

    # Со справкой active + cert_id — row рендерится со статусом и источником.
    ctx_with_cert = _minimal_context()
    ctx_with_cert["gnk_certificate"] = _Stub(
        status="active",
        source="uploaded",
        cert_id="GNK-2026-12345",
    )
    html_with_cert = tpl.render(**ctx_with_cert)
    assert "Справка ГНК" in html_with_cert
    assert "Активный плательщик НДС" in html_with_cert
    assert "GNK-2026-12345" in html_with_cert
    assert "загружено аналитиком" in html_with_cert


def test_template_handles_empty_observations() -> None:
    """Если ни strengths ни risks — рендерятся empty states."""
    env = _make_env()
    tpl = env.get_template("dossier.html")
    ctx = _minimal_context()
    ctx["observations"] = Observations(strengths=(), risks=())
    ctx["red_flags"] = []
    ctx["signal_breakdown"] = []
    html = tpl.render(**ctx)

    assert "Не выявлено выраженных позитивных индикаторов" in html
    assert "Сигналы не сработали" in html or "зелёной зоне" in html


def test_template_handles_missing_loan_request() -> None:
    env = _make_env()
    tpl = env.get_template("dossier.html")
    ctx = _minimal_context()
    ctx["loan_request"] = None
    html = tpl.render(**ctx)

    assert "BR-2026-0F8A" in html
    assert "Кредитная заявка" not in html


def test_template_renders_brand_name_in_header() -> None:
    """Brand-tenant: name/tagline/logo_mark подставляются из BrandConfig."""
    env = _make_env()
    tpl = env.get_template("dossier.html")
    html = tpl.render(**_minimal_context())

    assert "Uzbekbank Credit" in html
    assert "Bank Mode · Андижон" in html
    assert ">UB<" in html  # logo_mark в .logo-mark div
