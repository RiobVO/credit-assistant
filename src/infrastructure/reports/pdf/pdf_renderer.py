"""WeasyPrintPdfRenderer: HTML→PDF через WeasyPrint + Jinja2.

Имплементация ``application.ports.PdfReportPort.render``. Делает три вещи:

1. ``_build_context`` — превращает ``DossierPdfBundle`` в ``dict``, который
   ждёт шаблон ``templates/dossier.html`` (cover hero, identity stats,
   observations, KPI слоты, base64-чарт, метки).
2. Jinja2 рендер HTML.
3. WeasyPrint ``HTML(string=...).write_pdf()`` → bytes.

T0.4 / ADR-0015: per-render локаль резолвится через ``bundle.messages``
(``PdfMessages``). Closure-инжектные filters (``fmt_uzs``, ``fmt_date_ru``,
``severity_label``) пересобираются на каждый render — overhead микросекунды.
Template читает ``t = messages`` для всех локализованных строк, через
context-keys для pre-formatted (например ``methodology_body``).

Импорт WeasyPrint ленивый: на Windows-хосте без GTK runtime он падает,
но юнит-тесты на других слоях не должны страдать. Импорт триггерится
только при первом вызове ``render``.

Шрифты: Inter (400/500/600/700) и JetBrains Mono (500/600) забандлены в
``fonts/`` рядом с этим модулем (OFL, см. их LICENSE-файлы). `@font-face`
в шаблоне даёт WeasyPrint найти TTF через `base_url`, который мы выставляем
на директорию модуля. DejaVu остаётся резервом на случай, если в будущем
кто-то рендерит шаблон без bundle (CA-010).
"""

from __future__ import annotations

import base64
import logging
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jinja2

from application.dto.dossier_pdf_bundle import DossierPdfBundle
from application.dto.kpi_bundle import KpiUnit, KpiValue
from application.dto.pdf_messages import PdfMessages
from infrastructure.catalog.okved_catalog import default_catalog as default_okved_catalog
from infrastructure.reports.pdf import chart_renderer
from infrastructure.reports.pdf.template_filters import (
    fmt_inn,
    fmt_pct,
    fmt_pct_share,
    fmt_uzs_amount_only,
    make_fmt_date,
    make_fmt_date_month,
    make_fmt_date_short,
    make_fmt_datetime,
    make_fmt_uzs,
    make_severity_label,
    severity_bg,
    severity_color,
)

if TYPE_CHECKING:
    from application.use_cases.load_dossier_for_view import DossierViewBundle

PDF_DIR = Path(__file__).parent
TEMPLATES_DIR = PDF_DIR / "templates"
TEMPLATE_NAME = "dossier.html"
# WeasyPrint резолвит относительные URL из CSS (например, url('fonts/Inter-Regular.ttf'))
# относительно base_url. Делаем base_url абсолютным file:// URI на директорию pdf/ —
# работает одинаково на Windows-хосте и в Linux-контейнере (ADR-0008).
_BASE_URL = PDF_DIR.as_uri()

_logger = logging.getLogger(__name__)


class WeasyPrintPdfRenderer:
    """Sync PDF-renderer. Используется через ``asyncio.to_thread`` в use case."""

    def __init__(self, *, generated_at_factory: Any = None) -> None:
        # Фабрика timestamp'а — переопределяется в тестах для детерминизма.
        self._now = generated_at_factory or datetime.now
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=jinja2.select_autoescape(["html"]),
        )
        # Локало-независимые filters регистрируются один раз.
        self._env.filters["fmt_uzs_amount_only"] = fmt_uzs_amount_only
        self._env.filters["fmt_pct"] = fmt_pct
        self._env.filters["fmt_pct_share"] = fmt_pct_share
        self._env.filters["fmt_inn"] = fmt_inn
        self._env.filters["severity_color"] = severity_color
        self._env.filters["severity_bg"] = severity_bg

    def render(self, bundle: DossierPdfBundle) -> bytes:
        # Lazy import: WeasyPrint требует Pango/HarfBuzz, которые могут быть
        # недоступны на dev-хосте. Сам модуль импортируется без них.
        from weasyprint import HTML

        # T3.3: histogram WeasyPrint render time для Grafana dashboard.
        # Lazy import — domain/template-rendering layer не должен иметь
        # hard-dependency на observability infra.
        from infrastructure.observability.metrics import pdf_render_duration

        # T0.4: locale-зависимые filters пересобираются per-render через
        # closure'ы. Filter-registry env'а перезаписывается — env shared,
        # cost микросекунды.
        self._register_locale_filters(bundle.messages)

        context = self._build_context(bundle)
        html = self._env.get_template(TEMPLATE_NAME).render(**context)
        with pdf_render_duration.time():
            pdf_bytes: bytes = HTML(string=html, base_url=_BASE_URL).write_pdf()
        return pdf_bytes

    def _register_locale_filters(self, messages: PdfMessages) -> None:
        self._env.filters["fmt_uzs"] = make_fmt_uzs(messages)
        self._env.filters["fmt_date_ru"] = make_fmt_date(messages)
        self._env.filters["fmt_date_ru_short"] = make_fmt_date_short(messages)
        self._env.filters["fmt_date_ru_month"] = make_fmt_date_month(messages)
        self._env.filters["fmt_datetime_ru"] = make_fmt_datetime(messages)
        self._env.filters["severity_label"] = make_severity_label(messages)

    # ----------------------------- context build -----------------------------

    def _build_context(self, bundle: DossierPdfBundle) -> dict[str, object]:
        view_bundle = bundle.view_bundle
        view = view_bundle.view
        snapshot = view.snapshot
        dossier = view.dossier
        borrower = snapshot.borrower
        messages = bundle.messages

        application_id = view.case_id
        display_score = max(0, min(100, 100 - dossier.score))
        # Стрелка повторяет логику frontend score-gauge.tsx:
        # 0..100 → угол −90°..+90° (вертикаль вниз = 0).
        gauge_angle_deg = (display_score - 50) * 1.8

        # CA-046: пробрасываем «годовые есть?» в empty state чарта, чтобы
        # копирайт совпадал с UI досье (CA-036): различаем «нет помесячной
        # детализации» vs «нет данных о выручке вообще».
        chart_b64 = base64.b64encode(
            chart_renderer.render_revenue_24m(
                view_bundle.monthly_revenue_24m,
                messages,
                has_annual_revenue=view_bundle.kpis.revenue_ltm is not None,
            ),
        ).decode("ascii")

        okved_short, okved_full = _resolve_okved(borrower.oked_main, messages)
        region_city, region_district = _parse_region(
            borrower.registered_address, messages.region_district_full,
        )
        age_years, age_unit = _business_age(
            borrower.registration_date, snapshot.as_of, messages,
        )

        return {
            "t": messages,
            "lang": bundle.lang,
            "brand": bundle.brand,
            "application_id": application_id,
            "generated_at": self._now(),
            "borrower": borrower,
            "borrower_initials": _derive_initials(borrower.name),
            "snapshot": snapshot,
            "loan_request": snapshot.loan_request,
            # T0.3.2: ГНК-справка из snapshot. None если не загружена — template
            # рендерит row только когда есть, без placeholder'а.
            "gnk_certificate": snapshot.gnk_certificate,
            "rules_version": dossier.rules_version,
            "rules_evaluated": dossier.rules_evaluated,
            "rules_count": dossier.rules_evaluated,
            # Pre-formatted paragraphs (.format() с rules_count/rules_version):
            "methodology_body_text": messages.methodology_body.format(
                rules_count=dossier.rules_evaluated,
            ),
            "disclaimer_body_text": messages.disclaimer_body.format(
                rules_version=dossier.rules_version,
            ),
            "display_score": display_score,
            "gauge_angle_deg": f"{gauge_angle_deg:.2f}",
            "recommendation": dossier.recommendation,
            "recommendation_label": messages.recommendation.get(
                dossier.recommendation, dossier.recommendation,
            ),
            "signal_breakdown": _build_signal_breakdown(dossier.red_flags, messages),
            "legal_form_label": messages.legal_form_full.get(
                borrower.legal_form.value, borrower.legal_form.value,
            ),
            "legal_form_short": messages.legal_form_short.get(borrower.legal_form.value, "—"),
            "business_age_years": age_years,
            "business_age_unit": age_unit,
            "region_city": region_city,
            "region_district": region_district,
            "okved_short_label": okved_short,
            "okved_full_label": okved_full,
            "annual_reports": list(snapshot.annual_reports),
            "kpi_slots": _build_kpi_slots(view_bundle, messages),
            "chart_revenue_24m_b64": chart_b64,
            "top_buyers": list(bundle.top_buyers),
            "top_suppliers": list(bundle.top_suppliers),
            "tax_summary": bundle.tax_summary,
            "red_flags": _build_red_flags_view(dossier, bundle.rule_names, messages),
            "observations": bundle.observations,
        }


# ----------------------------- helpers --------------------------------------


def _derive_initials(name: str) -> str:
    """«ООО Полярная Звезда» → "ПЗ", «ИП Каримов А.» → "КА", «Артел» → "А".

    Игнорируем юр.префиксы (ООО, ЧП, АО, ИП, ОАО, ЗАО) и кавычки. Берём
    первую букву первых двух значимых слов. Если слово одно — одна буква.
    Не локализуется: префиксы фиксированы для UZ-банковской бумажной
    практики (кириллица).
    """
    junk = {"ООО", "ЧП", "АО", "ИП", "ОАО", "ЗАО", "Ltd"}
    tokens = [t.strip("«»\"'.,") for t in name.replace("«", " ").replace("»", " ").split()]
    significant = [t for t in tokens if t and t not in junk]
    if not significant:
        return "—"
    letters = [t[0].upper() for t in significant[:2]]
    return "".join(letters)


def _business_age(reg_date: date, as_of: date, messages: PdfMessages) -> tuple[int, str]:
    """Возраст компании в годах. Возвращает ``(N, unit)``.

    RU: год / года / лет (русский plural agreement); UZ: всегда «yil»
    (одна форма). Ключ выбирается на основе last_two/last_one — для UZ
    все три ключа резолвятся в одно и то же значение.
    """
    years = as_of.year - reg_date.year
    if (as_of.month, as_of.day) < (reg_date.month, reg_date.day):
        years -= 1
    years = max(years, 0)

    last_two = years % 100
    last_one = years % 10
    if 11 <= last_two <= 14:
        plural_key = "many"
    elif last_one == 1:
        plural_key = "one"
    elif 2 <= last_one <= 4:
        plural_key = "few"
    else:
        plural_key = "many"
    return years, messages.business_age_year[plural_key]


def _parse_region(address: str, district_full_word: str) -> tuple[str, str]:
    """«г. Ташкент, Юнусабадский р-н, ул. Амира Темура» → ("Ташкент", "Юнусабадский район").

    «р-н» → ``district_full_word`` (RU: «район»; UZ: «tuman»). Naive parsing
    для UZ-формата. Поддерживает два кейса:
      * Адрес с запятыми → берём первый сегмент как city, второй как district.
      * Адрес без запятых (фриформ из manual-input) → первый токен как city,
        остальное как district.
    """
    if not address or not address.strip():
        return ("—", "—")

    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) >= 2:
        city_part = parts[0]
        district_part = parts[1].replace("р-н", district_full_word).strip()
    else:
        tokens = [t for t in address.split() if t.strip()]
        if not tokens:
            return ("—", "—")
        city_part = tokens[0]
        district_part = (
            " ".join(tokens[1:]).replace("р-н", district_full_word).strip() or "—"
        )

    # Strip "г. " / "г." / "город " prefix из city.
    for prefix in ("г. ", "г.", "город "):
        if city_part.lower().startswith(prefix.lower()):
            city_part = city_part[len(prefix):].strip()
            break
    city_part = city_part.rstrip("^.,;:")

    return (city_part or "—", district_part or "—")


def _resolve_okved(code: str, messages: PdfMessages) -> tuple[str, str]:
    """OKVED код → (short_label, full_label). Unknown → (code, «—»).

    Источник — singleton-catalog (``default_okved_catalog``), JSON парсится
    один раз при первом обращении. Catalog хранит RU + UZ пары (CA-DS17);
    locale-picker берёт UZ для ``messages.locale == "uz"``, иначе RU.
    """
    entry = default_okved_catalog().get(code)
    if entry is None:
        return (code, "—")
    if messages.locale == "uz":
        return (entry.short_uz, entry.full_uz)
    return (entry.short_ru, entry.full_ru)


def _build_signal_breakdown(
    red_flags: tuple[Any, ...], messages: PdfMessages
) -> list[dict[str, object]]:
    """Returns ordered list of {severity, label, count} for «1 высокий · 2 средних».

    T0.4: единая форма per-severity из messages.signal_breakdown (UZ
    plural-agnostic; RU теряет singular/plural split — изначально кривое
    «1 критических», см. ADR-0015 Trade-offs).
    """
    counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for flag in red_flags:
        sev = str(flag.severity)
        if sev in counts:
            counts[sev] += 1

    out: list[dict[str, object]] = []
    for sev in ("critical", "high", "medium", "low"):
        n = counts[sev]
        if n == 0:
            continue
        word = messages.signal_breakdown.get(sev, sev)
        out.append({"severity": sev, "label": f"{n} {word}", "count": n})
    return out


def _build_kpi_slots(
    view_bundle: DossierViewBundle, messages: PdfMessages
) -> list[dict[str, object]]:
    """KPI карточки для PDF F-секции: legacy 4 (revenue_ltm / ebit / roe /
    debt_to_ebit) + ADR-0024 Session 1 6 (ebitda / debt_to_ebitda /
    current_ratio / working_capital / interest_coverage / dscr) + Session 2
    1 (quick_ratio) + Session 4 1 (fx_exposure_ratio). CA-037 invariant —
    legacy остаются рядом с расширением, не вместо. ADR-0024 Session 2:
    пустые слоты (kpi=None) скрываются после сборки — banker-clean view,
    align с UI поведением. Аналитик увидит «нет данных» в manual-input
    wizard, не в готовом PDF.

    Если значение ``None`` — карточка показывает «—» + локализованный hint.
    Универсальный `_kpi_slot` форматирует UZS/PCT/RATIO + level_tone (CA-048).
    """
    kpis = view_bundle.kpis
    fmt_uzs = make_fmt_uzs(messages)
    slots = [
        _kpi_slot("revenue_ltm", kpis.revenue_ltm, messages, fmt_uzs),
        _kpi_slot("ebit", kpis.ebit, messages, fmt_uzs),
        _kpi_slot("roe", kpis.roe, messages, fmt_uzs),
        _kpi_slot("debt_to_ebit", kpis.debt_to_ebit, messages, fmt_uzs),
        # ADR-0024 (Session 1): расширенная шестёрка.
        _kpi_slot("ebitda", kpis.ebitda, messages, fmt_uzs),
        _kpi_slot("debt_to_ebitda", kpis.debt_to_ebitda, messages, fmt_uzs),
        _kpi_slot("current_ratio", kpis.current_ratio, messages, fmt_uzs),
        _kpi_slot("working_capital", kpis.working_capital, messages, fmt_uzs),
        _kpi_slot("interest_coverage", kpis.interest_coverage, messages, fmt_uzs),
        _kpi_slot("dscr", kpis.dscr, messages, fmt_uzs),
        # ADR-0024 (Session 2):
        _kpi_slot("quick_ratio", kpis.quick_ratio, messages, fmt_uzs),
        # ADR-0024 (Session 4): FX Exposure Ratio (8-й KPI).
        _kpi_slot("fx_exposure_ratio", kpis.fx_exposure_ratio, messages, fmt_uzs),
    ]
    # ADR-0024 Session 2: hide empty cards — banker-clean PDF, align с UI.
    return [s for s in slots if s["value"] is not None]


def _kpi_slot(
    key: str,
    kpi: KpiValue | None,
    messages: PdfMessages,
    fmt_uzs: Any,
) -> dict[str, object]:
    label = messages.kpi_label.get(key, key)
    if kpi is None:
        return {
            "label": label,
            "value": None,
            "yoy_pct": None,
            "yoy_positive": False,
            "yoy_label": "",
            "level_tone": None,
        }
    if kpi.unit == KpiUnit.UZS:
        value_str = fmt_uzs(kpi.value, billions=True)
    elif kpi.unit == KpiUnit.PCT:
        value_str = fmt_pct(kpi.value)
    else:  # RATIO
        value_str = f"{kpi.value:.2f}".replace(".", ",")

    yoy_label = ""
    yoy_positive = False
    if kpi.yoy_pct is not None:
        yoy_positive = kpi.yoy_pct > 0
        yoy_label = fmt_pct(kpi.yoy_pct, with_sign=True)

    # CA-048: StrEnum.value → "good"/"warn"/"bad", совпадает с CSS-классами
    # .lvl-good/.lvl-warn/.lvl-bad в dossier.html. None → шаблон не добавит класс.
    level_tone = kpi.level_tone.value if kpi.level_tone is not None else None

    return {
        "label": label,
        "value": value_str,
        "yoy_pct": kpi.yoy_pct,
        "yoy_positive": yoy_positive,
        "yoy_label": yoy_label,
        "level_tone": level_tone,
    }


def _build_red_flags_view(
    dossier: Any, rule_names: dict[str, str], messages: PdfMessages
) -> list[dict[str, object]]:
    """RedFlag → flat dict для шаблона. ``rule_names`` маппит rule_id → human name
    (уже per-lang, резолвится в RenderDossierPdf).
    """
    severity_label = make_severity_label(messages)
    is_uz = messages.locale == "uz"
    rendered: list[dict[str, object]] = []
    for f in dossier.red_flags:
        sev_str = str(f.severity)
        # T0.4 follow-up B1: source локализуется. Для old snapshot'ов без
        # source_uz mapper подставил RU fallback (см. dossier_mapper).
        source_label = f.source_uz if is_uz and f.source_uz else f.source
        # T0.4 follow-up B2: message локализуется тем же шаблоном fallback'а.
        description_label = f.message_uz if is_uz and f.message_uz else f.message
        rendered.append(
            {
                "rule_id": f.rule_id,
                # Phase 10: human-readable заголовок из YAML вместо rule_id.
                "name": rule_names.get(f.rule_id, f.rule_id),
                "description": description_label,
                "severity": sev_str,
                "severity_label": severity_label(sev_str),
                "source": source_label,
                "evidence_value": _format_evidence_value(f.evidence, messages),
                "evidence_label": _format_evidence_label(f.evidence, messages),
            },
        )
    return rendered


# --- Evidence display contract --------------------------------------------
#
# Каждое правило кладёт в ``evidence`` все surfaces для аудитного трейла:
# vat_declared, sum_seller_esf_vat, diff_pct, period и т.д. PDF F-секция должна
# показать **одно** число справа от title — самое informative для аналитика.

_PRIMARY_EVIDENCE_KEYS: tuple[str, ...] = (
    "diff_pct",
    "yoy_pct",
    "vat_growth_pct",
    "margin",
    "max_supplier_share",
    "max_buyer_share",
    "ratio",
    "days_since_change",
    "shell_count",
    "cycle_count",
    "annual_reports_count",
    "equity",
    "loan",
)

_PCT_EVIDENCE_KEYS: frozenset[str] = frozenset({
    "diff_pct", "yoy_pct", "vat_growth_pct", "margin",
    "max_supplier_share", "max_buyer_share", "revenue_growth_pct",
})

_UZS_EVIDENCE_KEYS: frozenset[str] = frozenset({
    "equity", "loan", "revenue", "net_profit",
    "vat_declared", "sum_seller_esf_vat",
})


def _pick_primary_evidence(evidence: dict[str, Any]) -> tuple[str, Any] | None:
    """Возвращает (key, value) для primary-evidence или ``None``."""
    if not evidence:
        return None
    for k in _PRIMARY_EVIDENCE_KEYS:
        if k in evidence:
            return (k, evidence[k])
    for k, v in evidence.items():
        if not isinstance(v, (list, tuple, dict)):
            return (k, v)
    return None


def _format_evidence_value(evidence: dict[str, Any], messages: PdfMessages) -> str:
    """Форматирует primary-значение для F-секции (правый блок флага)."""
    from decimal import Decimal, InvalidOperation

    picked = _pick_primary_evidence(evidence)
    if picked is None:
        return ""
    key, value = picked

    # «infinity» из loan_to_revenue (deviser = 0).
    if key == "ratio" and str(value).lower() in ("infinity", "inf"):
        return "∞"

    if key in _PCT_EVIDENCE_KEYS:
        try:
            d = Decimal(str(value))
            return f"{d * 100:.0f}%"
        except (InvalidOperation, TypeError, ValueError) as exc:
            # Fallback на raw str — на проде debug-уровень для post-mortem,
            # почему конкретное evidence ушло в шаблон не отформатированным.
            _logger.debug(
                "pdf.format_fallback bucket=pct key=%s value=%r", key, value, exc_info=exc
            )

    if key in _UZS_EVIDENCE_KEYS:
        try:
            fmt_uzs = make_fmt_uzs(messages)
            return fmt_uzs(Decimal(str(value)), billions=True)
        except (InvalidOperation, TypeError, ValueError) as exc:
            _logger.debug(
                "pdf.format_fallback bucket=uzs key=%s value=%r", key, value, exc_info=exc
            )

    if key == "ratio":
        try:
            d = Decimal(str(value))
            return f"{d:.2f}".replace(".", ",")
        except (InvalidOperation, TypeError, ValueError) as exc:
            _logger.debug(
                "pdf.format_fallback bucket=ratio key=%s value=%r", key, value, exc_info=exc
            )

    return str(value)


def _format_evidence_label(evidence: dict[str, Any], messages: PdfMessages) -> str:
    """Локализованная метка под evidence-числом."""
    picked = _pick_primary_evidence(evidence)
    if picked is None:
        return ""
    key, _ = picked
    if key in messages.evidence_label:
        return messages.evidence_label[key]
    return key.replace("_", " ").capitalize()
