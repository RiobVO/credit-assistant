"""WeasyPrintPdfRenderer: HTML→PDF через WeasyPrint + Jinja2.

Имплементация ``application.ports.PdfReportPort.render``. Делает три вещи:

1. ``_build_context`` — превращает ``DossierPdfBundle`` в ``dict``, который
   ждёт шаблон ``templates/dossier.html`` (cover hero, identity stats,
   observations, KPI слоты, base64-чарт, метки).
2. Jinja2 рендер HTML.
3. WeasyPrint ``HTML(string=...).write_pdf()`` → bytes.

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
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jinja2

from application.dto.dossier_pdf_bundle import DossierPdfBundle
from application.dto.kpi_bundle import KpiUnit, KpiValue
from domain.entities.borrower import LegalForm
from infrastructure.catalog.okved_catalog import default_catalog as default_okved_catalog
from infrastructure.reports.pdf import chart_renderer
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

if TYPE_CHECKING:
    from application.use_cases.load_dossier_for_view import DossierViewBundle

PDF_DIR = Path(__file__).parent
TEMPLATES_DIR = PDF_DIR / "templates"
TEMPLATE_NAME = "dossier.html"
# WeasyPrint резолвит относительные URL из CSS (например, url('fonts/Inter-Regular.ttf'))
# относительно base_url. Делаем base_url абсолютным file:// URI на директорию pdf/ —
# работает одинаково на Windows-хосте и в Linux-контейнере (ADR-0008).
_BASE_URL = PDF_DIR.as_uri()

_RECOMMENDATION_LABEL = {
    "approve": "Одобрить",
    "review": "К пересмотру",
    "reject": "Отклонить",
}

_LEGAL_FORM_LABEL = {
    LegalForm.LLC: "Общество с ограниченной ответственностью",
    LegalForm.PE: "Частное предприятие",
    LegalForm.LTD: "Ltd",
    LegalForm.JSC: "Акционерное общество",
    LegalForm.IE: "Индивидуальный предприниматель",
    LegalForm.OTHER: "Иная форма",
}

_LEGAL_FORM_SHORT = {
    LegalForm.LLC: "ООО",
    LegalForm.PE: "ЧП",
    LegalForm.LTD: "Ltd",
    LegalForm.JSC: "АО",
    LegalForm.IE: "ИП",
    LegalForm.OTHER: "—",
}

_KPI_LABEL = {
    "revenue_ltm": "Revenue LTM",
    # CA-037: показываем EBIT-прокси до подключения D&A (FORM_5 / PROFIT_TAX).
    "ebit": "EBIT (прокси EBITDA)",
    "roe": "ROE",
    "debt_to_ebit": "Долг / EBIT",
}

# OKVED labels (CA-DS17): источник — ``config/okved/uz_msb.json`` через
# ``infrastructure.catalog.okved_catalog``. Синхронен с frontend OkvedAutocomplete
# (читает тот же JSON через ``GET /api/system/okved``). PDF использует RU
# (Phase 10 brand-tenant lock — banking output РУ-only).

_SIGNAL_BREAKDOWN_LABEL = {
    "critical": "критических",
    "high": "высокий",
    "medium": "средних",
    "low": "низкий",
}
_SIGNAL_PLURAL_LABEL = {
    "critical": "критических",
    "high": "высоких",
    "medium": "средних",
    "low": "низких",
}


class WeasyPrintPdfRenderer:
    """Sync PDF-renderer. Используется через ``asyncio.to_thread`` в use case."""

    def __init__(self, *, generated_at_factory: Any = None) -> None:
        # Фабрика timestamp'а — переопределяется в тестах для детерминизма.
        self._now = generated_at_factory or datetime.now
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=jinja2.select_autoescape(["html"]),
        )
        self._env.filters["fmt_uzs"] = fmt_uzs
        self._env.filters["fmt_uzs_amount_only"] = fmt_uzs_amount_only
        self._env.filters["fmt_pct"] = fmt_pct
        self._env.filters["fmt_pct_share"] = fmt_pct_share
        self._env.filters["fmt_date_ru"] = fmt_date_ru
        self._env.filters["fmt_date_ru_short"] = fmt_date_ru_short
        self._env.filters["fmt_date_ru_month"] = fmt_date_ru_month
        self._env.filters["fmt_datetime_ru"] = fmt_datetime_ru
        self._env.filters["fmt_inn"] = fmt_inn
        self._env.filters["severity_label"] = severity_label
        self._env.filters["severity_color"] = severity_color
        self._env.filters["severity_bg"] = severity_bg

    def render(self, bundle: DossierPdfBundle) -> bytes:
        # Lazy import: WeasyPrint требует Pango/HarfBuzz, которые могут быть
        # недоступны на dev-хосте. Сам модуль импортируется без них.
        from weasyprint import HTML

        context = self._build_context(bundle)
        html = self._env.get_template(TEMPLATE_NAME).render(**context)
        pdf_bytes: bytes = HTML(string=html, base_url=_BASE_URL).write_pdf()
        return pdf_bytes

    # ----------------------------- context build -----------------------------

    def _build_context(self, bundle: DossierPdfBundle) -> dict[str, object]:
        view_bundle = bundle.view_bundle
        view = view_bundle.view
        snapshot = view.snapshot
        dossier = view.dossier
        borrower = snapshot.borrower

        application_id = _format_application_id(view.dossier_id, view.created_at)
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
                has_annual_revenue=view_bundle.kpis.revenue_ltm is not None,
            ),
        ).decode("ascii")

        okved_short, okved_full = _resolve_okved(borrower.okved_main)
        region_city, region_district = _parse_region(borrower.registered_address)
        age_years, age_unit = _business_age(borrower.registration_date, snapshot.as_of)

        return {
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
            "display_score": display_score,
            "gauge_angle_deg": f"{gauge_angle_deg:.2f}",
            "recommendation": dossier.recommendation,
            "recommendation_label": _RECOMMENDATION_LABEL.get(
                dossier.recommendation, dossier.recommendation,
            ),
            "signal_breakdown": _build_signal_breakdown(dossier.red_flags),
            "legal_form_label": _LEGAL_FORM_LABEL.get(
                borrower.legal_form, borrower.legal_form.value,
            ),
            "legal_form_short": _LEGAL_FORM_SHORT.get(borrower.legal_form, "—"),
            "business_age_years": age_years,
            "business_age_unit": age_unit,
            "region_city": region_city,
            "region_district": region_district,
            "okved_short_label": okved_short,
            "okved_full_label": okved_full,
            "annual_reports": list(snapshot.annual_reports),
            "kpi_slots": _build_kpi_slots(view_bundle),
            "chart_revenue_24m_b64": chart_b64,
            "top_buyers": list(bundle.top_buyers),
            "top_suppliers": list(bundle.top_suppliers),
            "tax_summary": bundle.tax_summary,
            "red_flags": _build_red_flags_view(dossier, bundle.rule_names),
            "observations": bundle.observations,
        }


# ----------------------------- helpers --------------------------------------


def _format_application_id(dossier_id: object, created_at: datetime) -> str:
    """``BR-2026-XXXX`` где XXXX — первые 4 hex uuid в верхнем регистре."""
    suffix = str(dossier_id).replace("-", "")[:4].upper()
    return f"BR-{created_at.year}-{suffix}"


def _derive_initials(name: str) -> str:
    """«ООО Полярная Звезда» → "ПЗ", «ИП Каримов А.» → "КА", «Артел» → "А".

    Игнорируем юр.префиксы (ООО, ЧП, АО, ИП, ОАО, ЗАО) и кавычки. Берём
    первую букву первых двух значимых слов. Если слово одно — одна буква.
    """
    junk = {"ООО", "ЧП", "АО", "ИП", "ОАО", "ЗАО", "Ltd"}
    tokens = [t.strip("«»\"'.,") for t in name.replace("«", " ").replace("»", " ").split()]
    significant = [t for t in tokens if t and t not in junk]
    if not significant:
        return "—"
    letters = [t[0].upper() for t in significant[:2]]
    return "".join(letters)


def _business_age(reg_date: date, as_of: date) -> tuple[int, str]:
    """Возраст компании в годах. Возвращает ``(N, unit)`` где unit = «год»/«года»/«лет».

    Используется на cover stat-tile. Один год — «1 год», 2-4 — «2 года», 5+ —
    «5 лет», 11-14 — «лет» (русские падежи).
    """
    years = as_of.year - reg_date.year
    if (as_of.month, as_of.day) < (reg_date.month, reg_date.day):
        years -= 1
    years = max(years, 0)

    last_two = years % 100
    last_one = years % 10
    if 11 <= last_two <= 14:
        unit = "лет"
    elif last_one == 1:
        unit = "год"
    elif 2 <= last_one <= 4:
        unit = "года"
    else:
        unit = "лет"
    return years, unit


def _parse_region(address: str) -> tuple[str, str]:
    """«г. Ташкент, Юнусабадский р-н, ул. Амира Темура, д. 108» → ("Ташкент", "Юнусабадский район").

    Naive parsing для UZ-формата. Поддерживает два кейса:
      * Адрес с запятыми → берём первый сегмент как city, второй как district.
      * Адрес без запятых (фриформ из manual-input) → первый токен как city,
        остальное как district. Это лучше, чем сваливать всю строку в stat-num
        (22pt) и ломать визуальный rhythm 3-tile-grid (см. CA-DS17 lessons).
    Если структура не угадана, возвращаем ("—", "—").
    """
    if not address or not address.strip():
        return ("—", "—")

    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) >= 2:
        city_part = parts[0]
        district_part = parts[1].replace("р-н", "район").strip()
    else:
        # Single-segment fallback: split by whitespace, не по запятым.
        tokens = [t for t in address.split() if t.strip()]
        if not tokens:
            return ("—", "—")
        city_part = tokens[0]
        district_part = " ".join(tokens[1:]).replace("р-н", "район").strip() or "—"

    # Strip "г. " / "г." / "город " prefix из city (city = «Ташкент», не «г. Ташкент»).
    for prefix in ("г. ", "г.", "город "):
        if city_part.lower().startswith(prefix.lower()):
            city_part = city_part[len(prefix):].strip()
            break
    # Очистка noise-символов которые приходят из плохо нормализованного manual-input
    # (фикстуры показывали «Ташкент^» как литералку из формы Шага 1).
    city_part = city_part.rstrip("^.,;:")

    return (city_part or "—", district_part or "—")


def _resolve_okved(code: str) -> tuple[str, str]:
    """OKVED код → (short_label, full_label). Unknown → (code, «—»).

    Источник — singleton-catalog (``default_okved_catalog``), JSON парсится
    один раз при первом обращении. RU только — banking PDF РУ-локализован.
    """
    entry = default_okved_catalog().get(code)
    if entry is None:
        return (code, "—")
    return (entry.short_ru, entry.full_ru)


def _build_signal_breakdown(red_flags: tuple[Any, ...]) -> list[dict[str, object]]:
    """Returns ordered list of {severity, label, count} for «1 высокий · 2 средних · 1 низкий»."""
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
        word = _SIGNAL_BREAKDOWN_LABEL[sev] if n == 1 else _SIGNAL_PLURAL_LABEL[sev]
        out.append({"severity": sev, "label": f"{n} {word}", "count": n})
    return out


def _build_kpi_slots(view_bundle: DossierViewBundle) -> list[dict[str, object]]:
    """4 карточки в порядке: revenue_ltm / ebit / roe / debt_to_ebit.

    Если значение ``None`` — карточка показывает «—» + «Нет данных».
    """
    kpis = view_bundle.kpis
    return [
        _kpi_slot("revenue_ltm", kpis.revenue_ltm),
        _kpi_slot("ebit", kpis.ebit),
        _kpi_slot("roe", kpis.roe),
        _kpi_slot("debt_to_ebit", kpis.debt_to_ebit),
    ]


def _kpi_slot(key: str, kpi: KpiValue | None) -> dict[str, object]:
    if kpi is None:
        return {
            "label": _KPI_LABEL[key],
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
        "label": _KPI_LABEL[key],
        "value": value_str,
        "yoy_pct": kpi.yoy_pct,
        "yoy_positive": yoy_positive,
        "yoy_label": yoy_label,
        "level_tone": level_tone,
    }


def _build_red_flags_view(
    dossier: Any, rule_names: dict[str, str]
) -> list[dict[str, object]]:
    """RedFlag → flat dict для шаблона. ``rule_names`` маппит rule_id → human name."""
    rendered: list[dict[str, object]] = []
    for f in dossier.red_flags:
        sev_str = str(f.severity)
        rendered.append(
            {
                "rule_id": f.rule_id,
                # Phase 10: human-readable заголовок из YAML вместо rule_id.
                "name": rule_names.get(f.rule_id, f.rule_id),
                "description": f.message,
                "severity": sev_str,
                "severity_label": severity_label(sev_str),
                "source": f.source,
                "evidence_value": _format_evidence_value(f.evidence),
                "evidence_label": _format_evidence_label(f.evidence),
            },
        )
    return rendered


# --- Evidence display contract --------------------------------------------
#
# Каждое правило кладёт в ``evidence`` все surfaces для аудитного трейла:
# vat_declared, sum_seller_esf_vat, diff_pct, period и т.д. PDF F-секция должна
# показать **одно** число справа от title — самое informative для аналитика.
#
# Старый ``next(iter(...))`` тупо брал первый ключ — это давало в PDF Python
# repr list-литералов («['2026-03-01', '2026-03-31']» вместо «23%»). Новая
# логика: whitelist primary-ключей по приоритету + типизированный форматтер.

# Приоритет ключей — первый match выигрывает. delta-метрики (diff/yoy/margin)
# и счётчики идут перед абсолютными величинами и list-полями (period/quarters).
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

_EVIDENCE_LABEL_RU: dict[str, str] = {
    "diff_pct": "Разрыв",
    "yoy_pct": "YoY",
    "vat_growth_pct": "Рост НДС",
    "margin": "Маржа",
    "max_supplier_share": "Доля топ-1",
    "max_buyer_share": "Доля топ-1",
    "ratio": "К выручке",
    "days_since_change": "Дней назад",
    "shell_count": "Контрагентов",
    "cycle_count": "Циклов",
    "annual_reports_count": "Годовых отчётов",
    "equity": "Капитал",
    "loan": "Сумма заявки",
}


def _pick_primary_evidence(evidence: dict[str, Any]) -> tuple[str, Any] | None:
    """Возвращает (key, value) для primary-evidence или ``None``."""
    if not evidence:
        return None
    for k in _PRIMARY_EVIDENCE_KEYS:
        if k in evidence:
            return (k, evidence[k])
    # Fallback: первый scalar (не list/tuple/dict — не отрисуем красиво).
    for k, v in evidence.items():
        if not isinstance(v, (list, tuple, dict)):
            return (k, v)
    return None


def _format_evidence_value(evidence: dict[str, Any]) -> str:
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
        except (InvalidOperation, TypeError, ValueError):
            pass

    if key in _UZS_EVIDENCE_KEYS:
        try:
            return fmt_uzs(Decimal(str(value)), billions=True)
        except (InvalidOperation, TypeError, ValueError):
            pass

    if key == "ratio":
        try:
            d = Decimal(str(value))
            return f"{d:.2f}".replace(".", ",")
        except (InvalidOperation, TypeError, ValueError):
            pass

    return str(value)


def _format_evidence_label(evidence: dict[str, Any]) -> str:
    """RU-метка под evidence-числом."""
    picked = _pick_primary_evidence(evidence)
    if picked is None:
        return ""
    key, _ = picked
    if key in _EVIDENCE_LABEL_RU:
        return _EVIDENCE_LABEL_RU[key]
    return key.replace("_", " ").capitalize()
