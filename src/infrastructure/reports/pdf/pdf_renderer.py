"""WeasyPrintPdfRenderer: HTML→PDF через WeasyPrint + Jinja2.

Имплементация ``application.ports.PdfReportPort.render``. Делает три вещи:

1. ``_build_context`` — превращает ``DossierPdfBundle`` в ``dict``, который
   ждёт шаблон ``templates/dossier.html`` (KPI слоты, base64-чарт, метки).
2. Jinja2 рендер HTML.
3. WeasyPrint ``HTML(string=...).write_pdf()`` → bytes.

Импорт WeasyPrint ленивый: на Windows-хосте без GTK runtime он падает,
но юнит-тесты на других слоях не должны страдать. Импорт триггерится
только при первом вызове ``render``.

Шрифты: цепочка ``Inter → DejaVu Sans`` живёт в самом шаблоне. Если в
будущем подключим Inter через bundle TTF — нужен FontConfig
(см. ADR 0008, TODO[CA-010]).
"""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jinja2

from application.dto.dossier_pdf_bundle import DossierPdfBundle
from application.dto.kpi_bundle import KpiUnit, KpiValue
from infrastructure.reports.pdf import chart_renderer
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

if TYPE_CHECKING:
    from application.use_cases.load_dossier_for_view import DossierViewBundle

TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATE_NAME = "dossier.html"

_RECOMMENDATION_LABEL = {
    "approve": "Одобрить",
    "review": "К пересмотру",
    "reject": "Отклонить",
}

_LEGAL_FORM_LABEL = {
    "llc": "ООО (Общество с ограниченной ответственностью)",
    "pe": "ЧП (Частное предприятие)",
    "ltd": "Ltd",
    "jsc": "АО (Акционерное общество)",
    "ie": "ИП (Индивидуальный предприниматель)",
    "other": "Иная форма",
}

_KPI_LABEL = {
    "revenue_ltm": "Revenue LTM",
    "ebitda": "EBITDA",
    "roe": "ROE",
    "debt_to_ebitda": "Debt / EBITDA",
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
        self._env.filters["fmt_pct"] = fmt_pct
        self._env.filters["fmt_pct_share"] = fmt_pct_share
        self._env.filters["fmt_date_ru"] = fmt_date_ru
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
        pdf_bytes: bytes = HTML(string=html).write_pdf()
        return pdf_bytes

    # ----------------------------- context build -----------------------------

    def _build_context(self, bundle: DossierPdfBundle) -> dict[str, object]:
        view_bundle = bundle.view_bundle
        view = view_bundle.view
        snapshot = view.snapshot
        dossier = view.dossier

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

        return {
            "application_id": application_id,
            "generated_at": self._now(),
            "status_label": "На рассмотрении",
            "borrower": snapshot.borrower,
            "snapshot": snapshot,
            "loan_request": snapshot.loan_request,
            "rules_version": dossier.rules_version,
            "rules_evaluated": dossier.rules_evaluated,
            "display_score": display_score,
            "gauge_angle_deg": f"{gauge_angle_deg:.2f}",
            "recommendation": dossier.recommendation,
            "recommendation_label": _RECOMMENDATION_LABEL.get(
                dossier.recommendation, dossier.recommendation,
            ),
            "red_flags_count_label": _format_red_flags_label(dossier),
            "legal_form_label": _LEGAL_FORM_LABEL.get(
                snapshot.borrower.legal_form.value, snapshot.borrower.legal_form.value,
            ),
            "annual_reports": list(snapshot.annual_reports),
            "kpi_slots": _build_kpi_slots(view_bundle),
            "chart_revenue_24m_b64": chart_b64,
            "top_buyers": list(bundle.top_buyers),
            "top_suppliers": list(bundle.top_suppliers),
            "tax_summary": bundle.tax_summary,
            "red_flags": _build_red_flags_view(dossier),
        }


# ----------------------------- helpers --------------------------------------


def _format_application_id(dossier_id: object, created_at: datetime) -> str:
    """``BR-2026-XXXX`` где XXXX — первые 4 hex uuid в верхнем регистре."""
    suffix = str(dossier_id).replace("-", "")[:4].upper()
    return f"BR-{created_at.year}-{suffix}"


def _format_red_flags_label(dossier: Any) -> str:
    n = len(dossier.red_flags)
    if n == 0:
        return "Сигналы не сработали — заёмщик в зелёной зоне."
    parts: list[str] = []
    for sev in ("critical", "high", "medium", "low"):
        count = sum(1 for f in dossier.red_flags if str(f.severity) == sev)
        if count:
            parts.append(f"{count} {severity_label(sev).lower()}")
    return f"{n} сработавших сигнала: " + " · ".join(parts)


def _build_kpi_slots(view_bundle: DossierViewBundle) -> list[dict[str, object]]:
    """4 карточки в порядке: revenue_ltm / ebitda / roe / debt_to_ebitda.

    Если значение ``None`` — карточка показывает «—» + «Нет данных».
    """
    kpis = view_bundle.kpis
    return [
        _kpi_slot("revenue_ltm", kpis.revenue_ltm),
        _kpi_slot("ebitda", kpis.ebitda),
        _kpi_slot("roe", kpis.roe),
        _kpi_slot("debt_to_ebitda", kpis.debt_to_ebitda),
    ]


def _kpi_slot(key: str, kpi: KpiValue | None) -> dict[str, object]:
    if kpi is None:
        return {
            "label": _KPI_LABEL[key],
            "value": None,
            "yoy_pct": None,
            "yoy_positive": False,
            "yoy_label": "",
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

    return {
        "label": _KPI_LABEL[key],
        "value": value_str,
        "yoy_pct": kpi.yoy_pct,
        "yoy_positive": yoy_positive,
        "yoy_label": yoy_label,
    }


def _build_red_flags_view(dossier: Any) -> list[dict[str, object]]:
    """RedFlag → flat dict для шаблона."""
    rendered: list[dict[str, object]] = []
    for f in dossier.red_flags:
        rendered.append(
            {
                "rule_id": f.rule_id,
                "name": f.rule_id,  # человеческого имени нет в RedFlag — кладём rule_id
                "description": f.message,
                "severity": str(f.severity),
                "source": f.source,
                "evidence_value": _format_evidence_value(f.evidence),
                "evidence_label": _format_evidence_label(f.evidence),
            },
        )
    return rendered


def _format_evidence_value(evidence: dict[str, Any]) -> str:
    """Берёт первое значение из evidence-словаря и приводит к строке."""
    if not evidence:
        return ""
    return str(next(iter(evidence.values())))


def _format_evidence_label(evidence: dict[str, Any]) -> str:
    """Метка под evidence-числом — ключ первого поля в evidence-словаре."""
    if not evidence:
        return ""
    return next(iter(evidence.keys()))
