"""KpiBundle: набор KPI-показателей для экрана досье (Phase 3.B / CA-037).

Read-only DTO, заполняется ``application.services.kpi_calculator``. Все
поля nullable — degraded mode по правилу A (Phase 3.B Q2): если данных
недостаточно для расчёта, возвращаем ``None``, а UI показывает empty card.

CA-037: вместо ``ebitda`` экспортируем ``ebit`` — EBIT прокси для EBITDA до
тех пор пока depreciation/amortization не доступен (требует FORM_5 cashflow
parser, не покрыт PROFIT_TAX scope). Имя поля честное: семантически это
**EBIT** = PBT + interest_expense. Когда D&A появится — добавим отдельные
поля ``ebitda`` / ``debt_to_ebitda`` рядом, не переименовывая существующие.

``debt_to_ebit`` ratio = total_debt / EBIT_LTM. Семантика 4 кейсов:
* total_debt = None → KPI None (UI: «Загрузите Форму №1»);
* total_debt = 0 → KPI Decimal("0") (UI: green «Нет долга»);
* EBIT ≤ 0 → KPI None (убыток, оценка некорректна);
* иначе → Decimal ratio в формате ``X.XX``.

ADR-0024 (Session 1) добавил 6 расширенных KPI **рядом** с legacy парой
``ebit``/``debt_to_ebit`` (CA-037 invariant: не переименовываем, добавляем):

* ``ebitda`` = ``profit_before_tax + interest_expense + depreciation_amortization``.
  D&A nullable в ``FinancialReport`` — если отсутствует, ``ebitda = None`` (не
  fallback на EBIT: пользователь должен явно видеть «нет D&A → нет EBITDA»).
* ``debt_to_ebitda`` = ``total_debt / EBITDA``. Аналог ``debt_to_ebit``, но с
  более правильным знаменателем. Пороги: <3× GOOD / 3..5 WARN / >5× BAD
  (Basel III IRB).
* ``current_ratio`` = ``current_assets / current_liabilities``. Пороги:
  >1.5 GOOD / 1.0..1.5 WARN / <1.0 BAD (IFC SME ch.4).
* ``working_capital`` = ``current_assets − current_liabilities``. Money-KPI
  без universal threshold — level_tone=None.
* ``interest_coverage`` = ``EBIT / interest_expense``. Пороги: >3 GOOD /
  1.5..3 WARN / <1.5 BAD (Basel III IRB).
* ``dscr`` = ``OCF / annual_debt_service`` (fallback chain OCF → EBITDA → EBIT
  такая же, как в правиле DSCR_LOW). Пороги: >1.5 GOOD / 1.2..1.5 WARN / <1.2
  BAD (Murodov O.J. 2025 + IFC SME ch.4).

Тред «KPI None» сохраняется во всей расширенной шестёрке: любой отсутствующий
компонент → ``None``; делитель ≤ 0 → ``None``. EBITDA ≤ 0 проксирует «нет
покрытия» — ``debt_to_ebitda`` тогда тоже ``None``.

CA-048: ``KpiValue.level_tone`` — ортогональный сигнал «absolute level»
для UI/PDF (left severity stripe). Заполняется только для ROE и
Debt-to-EBIT; для revenue/ebit остаётся ``None`` (нет универсального
порога для абсолютной величины). Источник порогов: Базель III IRB
(leverage / capital adequacy) + внутренние методики банков-партнёров.
Boundary inclusive на верхней границе warn — пограничные значения
банк лучше держит в осторожной зоне.
* **ROE**: ``>15% → GOOD``, ``5 ≤ ROE ≤ 15 → WARN``, ``<5% → BAD``.
* **Debt/EBIT**: ``<2× → GOOD``, ``2 ≤ ratio ≤ 4 → WARN``, ``>4× → BAD``;
  ``Decimal(0)`` («нет долга») → GOOD (но UI рендерит спец-карточку
  ``NoDebtCard``, level_tone GOOD здесь — теоретическая консистентность,
  не визуальный канал).
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


class KpiLevelTone(StrEnum):
    """Категория абсолютного уровня KPI (CA-048). См. модуль-docstring."""

    GOOD = "good"
    WARN = "warn"
    BAD = "bad"


@dataclass(frozen=True, slots=True)
class KpiValue:
    value: Decimal
    unit: KpiUnit
    yoy_pct: Decimal | None  # знак: + рост, − падение; None если сравнивать не с чем
    sparkline: tuple[Decimal, ...]  # точки динамики, oldest → newest; может быть пустой
    # CA-048: категория absolute-level порога. None для KPI без универсального
    # threshold (revenue_ltm, ebit). Для ROE/Debt-to-EBIT — см. модуль-docstring.
    level_tone: KpiLevelTone | None = None


@dataclass(frozen=True, slots=True)
class KpiBundle:
    revenue_ltm: KpiValue | None
    ebit: KpiValue | None  # CA-037: PBT + interest_expense (прокси EBITDA до FORM_5)
    roe: KpiValue | None
    debt_to_ebit: KpiValue | None  # CA-037: total_debt / EBIT_LTM
    # ADR-0024 (Session 1): расширенные KPI рядом с legacy парой.
    ebitda: KpiValue | None = None  # PBT + interest_expense + D&A
    debt_to_ebitda: KpiValue | None = None  # total_debt / EBITDA
    current_ratio: KpiValue | None = None  # current_assets / current_liabilities
    working_capital: KpiValue | None = None  # current_assets − current_liabilities (UZS)
    interest_coverage: KpiValue | None = None  # EBIT / interest_expense
    dscr: KpiValue | None = None  # OCF / debt_service_annual (fallback EBITDA → EBIT)
    # ADR-0024 (Session 2): Quick Ratio (acid-test ratio).
    quick_ratio: KpiValue | None = None  # (current_assets − inventory) / current_liabilities


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
