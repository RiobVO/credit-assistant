"""KpiBundle: набор KPI-показателей для экрана досье (Phase 3.B / CA-037).

Read-only DTO, заполняется ``application.services.kpi_calculator``. Все
поля nullable — degraded mode по правилу A (Phase 3.B Q2): если данных
недостаточно для расчёта, возвращаем ``None``, а UI показывает empty card.

CA-037: вместо ``ebitda`` экспортируем ``ebit`` — EBIT прокси для EBITDA до
тех пор пока depreciation/amortization не доступен (нужен FORM_5 cashflow
или PROFIT_TAX с D&A разбивкой, TODO[CA-029b]). Имя поля честное: семантически
это **EBIT** = PBT + interest_expense. Когда D&A появится — добавим отдельные
поля ``ebitda`` / ``debt_to_ebitda`` рядом, не переименовывая существующие.

``debt_to_ebit`` ratio = total_debt / EBIT_LTM. Семантика 4 кейсов:
* total_debt = None → KPI None (UI: «Загрузите Форму №1»);
* total_debt = 0 → KPI Decimal("0") (UI: green «Нет долга»);
* EBIT ≤ 0 → KPI None (убыток, оценка некорректна);
* иначе → Decimal ratio в формате ``X.XX``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class KpiUnit(StrEnum):
    UZS = "UZS"
    PCT = "PCT"
    RATIO = "RATIO"


@dataclass(frozen=True, slots=True)
class KpiValue:
    value: Decimal
    unit: KpiUnit
    yoy_pct: Decimal | None  # знак: + рост, − падение; None если сравнивать не с чем
    sparkline: tuple[Decimal, ...]  # точки динамики, oldest → newest; может быть пустой


@dataclass(frozen=True, slots=True)
class KpiBundle:
    revenue_ltm: KpiValue | None
    ebit: KpiValue | None  # CA-037: PBT + interest_expense (прокси EBITDA до FORM_5)
    roe: KpiValue | None
    debt_to_ebit: KpiValue | None  # CA-037: total_debt / EBIT_LTM


@dataclass(frozen=True, slots=True)
class MonthlyRevenuePoint:
    """Одна точка чарта «Выручка 24 мес» на экране досье.

    ``trend`` — 12-мес rolling average по revenue (для линии-тренда поверх
    столбцов). Если меньше 12 точек до текущей — average по доступным.

    ``is_peak`` — точка попадает в top-3 по выручке внутри отображаемого окна.
    UI рисует такие столбцы акцентным цветом.
    """

    month_start: date
    revenue: Decimal
    trend: Decimal
    is_peak: bool
