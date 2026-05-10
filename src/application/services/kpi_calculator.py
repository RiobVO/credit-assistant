"""KPI-калькулятор для экрана досье (Phase 3.B).

Pure function над ``BorrowerSnapshot``: выдаёт ``KpiBundle`` для GET
/api/dossier/{id}. Domain не зависит от этого модуля.

Что считаем (degraded-aware, правило A):
* ``revenue_ltm`` — приоритет ``monthly_turnover`` (последние 12 месяцев),
  fallback на последний ``annual_report``. Если нет ни того, ни другого →
  ``None``.
* ``ebitda`` / ``roe`` / ``debt_to_ebitda`` — сейчас всегда ``None``: компоненты
  (EBITDA, equity, debt short/long term) не выделены в snapshot. Заведём,
  когда появятся данные Form 1 / Form 2.

Все деньги в snapshot — ``Money`` с ``Currency``. Здесь работаем только с
``UZS`` записями (ETL гарантирует UZS для МСБ Узбекистана; non-UZS — редкая
эксцеция, в Phase 3.B игнорируем).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from application.dto.kpi_bundle import (
    KpiBundle,
    KpiUnit,
    KpiValue,
    MonthlyRevenuePoint,
)
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.value_objects.money import Currency


def compute_kpis(snapshot: BorrowerSnapshot) -> KpiBundle:
    """Считает KPI-набор для экрана досье. ``snapshot.as_of`` определяет
    «сейчас» — но фактически берём самые свежие данные из коллекций (адаптеры
    могут прислать данные старше as_of, и это нормально для исторического
    прогона).
    """
    return KpiBundle(
        revenue_ltm=_compute_revenue_ltm(snapshot),
        ebitda=None,
        roe=None,
        debt_to_ebitda=None,
    )


def _compute_revenue_ltm(snapshot: BorrowerSnapshot) -> KpiValue | None:
    monthly_uzs = _filter_uzs_monthly(snapshot.monthly_turnover)
    if len(monthly_uzs) >= 12:
        return _ltm_from_monthly(monthly_uzs)

    annual_uzs = _filter_uzs_annual(snapshot.annual_reports)
    if annual_uzs:
        return _ltm_from_annual(annual_uzs)

    return None


def _filter_uzs_monthly(items: Sequence[MonthlyTurnover]) -> list[MonthlyTurnover]:
    return [m for m in items if m.revenue.currency is Currency.UZS]


def _filter_uzs_annual(items: Sequence[FinancialReport]) -> list[FinancialReport]:
    return [a for a in items if a.revenue.currency is Currency.UZS]


def _ltm_from_monthly(monthly: Sequence[MonthlyTurnover]) -> KpiValue:
    """Sum последних 12 месяцев. YoY с предшествующими 12, если есть."""
    sorted_desc = sorted(monthly, key=lambda m: m.month_start, reverse=True)
    last_12 = sorted_desc[:12]
    ltm_total = sum((m.revenue.amount for m in last_12), start=Decimal(0))

    yoy_pct: Decimal | None = None
    if len(sorted_desc) >= 24:
        prev_12 = sorted_desc[12:24]
        prev_total = sum((m.revenue.amount for m in prev_12), start=Decimal(0))
        if prev_total != 0:
            yoy_pct = (ltm_total - prev_total) / prev_total * Decimal(100)

    # Sparkline: последние 12 точек oldest → newest, для UI.
    sparkline = tuple(m.revenue.amount for m in reversed(last_12))

    return KpiValue(
        value=ltm_total,
        unit=KpiUnit.UZS,
        yoy_pct=yoy_pct,
        sparkline=sparkline,
    )


def _ltm_from_annual(annual: Sequence[FinancialReport]) -> KpiValue:
    """Fallback: последний годовой отчёт. YoY с предыдущим, если есть."""
    sorted_desc = sorted(annual, key=lambda a: a.period.start, reverse=True)
    latest = sorted_desc[0]
    value = latest.revenue.amount

    yoy_pct: Decimal | None = None
    if len(sorted_desc) >= 2:
        prev_value = sorted_desc[1].revenue.amount
        if prev_value != 0:
            yoy_pct = (value - prev_value) / prev_value * Decimal(100)

    return KpiValue(
        value=value,
        unit=KpiUnit.UZS,
        yoy_pct=yoy_pct,
        sparkline=(),  # годовые не дают полезной sparkline
    )


def compute_monthly_revenue_24m(
    snapshot: BorrowerSnapshot,
) -> tuple[MonthlyRevenuePoint, ...]:
    """Чарт «Выручка 24 мес» для экрана досье.

    Берёт последние 24 ``MonthlyTurnover`` (UZS-only) в хронологическом порядке.
    Для каждой точки вычисляет 12-мес rolling average (тренд) — по доступным
    предыдущим точкам (если до текущей меньше 12, average по тому что есть).

    Top-3 по revenue в выборке помечаются ``is_peak=True`` — UI рисует
    акцентным цветом. Если данных меньше 24 — отдаём что есть; пустой массив,
    если monthly_turnover пустой или не содержит UZS.
    """
    monthly_uzs = sorted(
        _filter_uzs_monthly(snapshot.monthly_turnover),
        key=lambda m: m.month_start,
    )
    last_24 = monthly_uzs[-24:]
    if not last_24:
        return ()

    revenues = [m.revenue.amount for m in last_24]

    # Top-3 индексы по revenue: устойчивая сортировка → если несколько с равной
    # суммой, peak становится первый по дате.
    top_indices = set(
        sorted(range(len(revenues)), key=lambda i: revenues[i], reverse=True)[:3]
    )

    points: list[MonthlyRevenuePoint] = []
    for i, m in enumerate(last_24):
        window = revenues[max(0, i - 11) : i + 1]
        trend = sum(window, Decimal(0)) / Decimal(len(window))
        points.append(
            MonthlyRevenuePoint(
                month_start=m.month_start,
                revenue=m.revenue.amount,
                trend=trend,
                is_peak=i in top_indices,
            )
        )
    return tuple(points)
