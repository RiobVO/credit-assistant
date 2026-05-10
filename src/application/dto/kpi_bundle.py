"""KpiBundle: набор KPI-показателей для экрана досье (Phase 3.B).

Read-only DTO, заполняется ``application.services.kpi_calculator``. Все четыре
поля nullable — degraded mode по правилу A (см. Phase 3.B Q2): если данных
недостаточно для расчёта, возвращаем ``None``, а UI показывает «—» в карточке.

В Phase 3.B считаем только ``revenue_ltm`` (есть в данных). EBITDA / ROE /
Debt-to-EBITDA остаются ``None`` — их компоненты (EBITDA, equity, debt
short/long term) не выделены отдельно в текущем snapshot. Поднимем когда
появятся данные Form 1 / Form 2 в snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    ebitda: KpiValue | None
    roe: KpiValue | None
    debt_to_ebitda: KpiValue | None
