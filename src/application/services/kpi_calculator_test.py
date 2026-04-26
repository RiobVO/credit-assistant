"""Тесты KPI-калькулятора для экрана досье (Phase 3.B).

Покрывают три источника данных revenue_ltm:
* monthly_turnover ≥ 12 → LTM из последних 12 + sparkline + YoY
* annual_reports → fallback, sparkline пустая
* нет данных → None

И факт degraded для трёх вторичных KPI (всегда None в Phase 3.B).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from application.dto.kpi_bundle import KpiLevelTone, KpiUnit
from application.services.kpi_calculator import (
    compute_kpis,
    compute_monthly_revenue_24m,
)
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS
USD = Currency.USD


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("306399449"),
        name="ООО Тест",
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 1, 1),
        director_name="Иванов И.И.",
        director_appointed_at=date(2020, 1, 1),
        okved_main="62.01",
        registered_address="г. Ташкент",
    )


def _monthly(month_start: date, amount: int, currency: Currency = UZS) -> MonthlyTurnover:
    return MonthlyTurnover(
        month_start=month_start,
        revenue=Money(Decimal(amount), currency),
    )


def _annual(year: int, revenue: int) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=Money(Decimal(revenue), UZS),
        net_profit=Money(Decimal(revenue // 10), UZS),
        taxes_paid=Money(Decimal(revenue // 20), UZS),
    )


def _snapshot(
    *,
    monthly: list[MonthlyTurnover] | None = None,
    annual: list[FinancialReport] | None = None,
    as_of: date = date(2026, 5, 8),
) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=_borrower(),
        as_of=as_of,
        monthly_turnover=monthly or [],
        annual_reports=annual or [],
    )


# ----------- revenue_ltm: monthly_turnover priority ----------------------------


def test_revenue_ltm_from_12_months_no_yoy() -> None:
    """12 месяцев данных → LTM = sum, sparkline 12 точек oldest→newest, YoY=None."""
    monthly = [_monthly(date(2025, m, 1), 1_000_000_000) for m in range(6, 13)]
    monthly += [_monthly(date(2026, m, 1), 1_500_000_000) for m in range(1, 6)]
    # 12 записей: 7 за 2025-06..12 и 5 за 2026-01..05.
    assert len(monthly) == 12

    bundle = compute_kpis(_snapshot(monthly=monthly))

    assert bundle.revenue_ltm is not None
    assert bundle.revenue_ltm.unit is KpiUnit.UZS
    expected_total = Decimal(7) * Decimal(1_000_000_000) + Decimal(5) * Decimal(1_500_000_000)
    assert bundle.revenue_ltm.value == expected_total
    assert bundle.revenue_ltm.yoy_pct is None  # нет prev_12
    assert len(bundle.revenue_ltm.sparkline) == 12
    # sparkline oldest → newest: первая точка = 2025-06 (1B), последняя = 2026-05 (1.5B)
    assert bundle.revenue_ltm.sparkline[0] == Decimal(1_000_000_000)
    assert bundle.revenue_ltm.sparkline[-1] == Decimal(1_500_000_000)


def test_revenue_ltm_24_months_computes_yoy() -> None:
    """24 месяца → YoY как отношение LTM к prev_LTM."""
    # 12 месяцев old (2024): по 1B каждый = 12B
    old = [_monthly(date(2024, m, 1), 1_000_000_000) for m in range(1, 13)]
    # 12 месяцев new (2025): по 1.2B = 14.4B
    new = [_monthly(date(2025, m, 1), 1_200_000_000) for m in range(1, 13)]

    bundle = compute_kpis(_snapshot(monthly=old + new, as_of=date(2026, 1, 1)))

    assert bundle.revenue_ltm is not None
    assert bundle.revenue_ltm.value == Decimal("14400000000")
    # YoY = (14.4B - 12B) / 12B * 100 = +20%
    assert bundle.revenue_ltm.yoy_pct == Decimal(20)


def test_revenue_ltm_unsorted_input_takes_most_recent_12() -> None:
    """Калькулятор сортирует по month_start desc — порядок входа неважен."""
    monthly = [
        _monthly(date(2026, 5, 1), 5_000),
        _monthly(date(2025, 6, 1), 1_000),
        _monthly(date(2026, 1, 1), 3_000),
    ] * 5  # 15 записей в случайном порядке
    monthly = monthly[:12]  # ровно 12 для покрытия порога

    bundle = compute_kpis(_snapshot(monthly=monthly))

    assert bundle.revenue_ltm is not None
    # Сумма всех 12 — точная независимо от порядка
    assert bundle.revenue_ltm.value == sum((m.revenue.amount for m in monthly), Decimal(0))


def test_revenue_ltm_ignores_non_uzs() -> None:
    """USD записи фильтруются — Phase 3.B работает только с UZS."""
    monthly = [_monthly(date(2025, m, 1), 1_000_000_000) for m in range(1, 13)]
    monthly.append(_monthly(date(2026, 1, 1), 100_000, currency=USD))
    # 12 UZS + 1 USD; USD не учитывается, остаётся 12 валидных

    bundle = compute_kpis(_snapshot(monthly=monthly))

    assert bundle.revenue_ltm is not None
    assert bundle.revenue_ltm.value == Decimal(12) * Decimal(1_000_000_000)


# ----------- revenue_ltm: annual fallback --------------------------------------


def test_revenue_ltm_from_annual_when_monthly_insufficient() -> None:
    """<12 monthly → fallback на последний годовой, sparkline пустая."""
    monthly = [_monthly(date(2025, m, 1), 5_000_000) for m in range(1, 4)]  # только 3
    annual = [_annual(2024, 18_000_000_000), _annual(2025, 24_000_000_000)]

    bundle = compute_kpis(_snapshot(monthly=monthly, annual=annual))

    assert bundle.revenue_ltm is not None
    assert bundle.revenue_ltm.value == Decimal("24000000000")
    # YoY = (24 - 18) / 18 * 100 ≈ 33.33...
    assert bundle.revenue_ltm.yoy_pct is not None
    assert bundle.revenue_ltm.yoy_pct.quantize(Decimal("0.01")) == Decimal("33.33")
    assert bundle.revenue_ltm.sparkline == ()


def test_revenue_ltm_single_annual_no_yoy() -> None:
    """Один годовой → revenue есть, YoY None."""
    bundle = compute_kpis(_snapshot(annual=[_annual(2025, 10_000_000_000)]))

    assert bundle.revenue_ltm is not None
    assert bundle.revenue_ltm.value == Decimal("10000000000")
    assert bundle.revenue_ltm.yoy_pct is None


# ----------- revenue_ltm: full degraded ----------------------------------------


def test_revenue_ltm_returns_none_without_data() -> None:
    """Ни monthly_turnover, ни annual → None."""
    bundle = compute_kpis(_snapshot())

    assert bundle.revenue_ltm is None


# ----------- CA-037: EBIT / ROE / Debt-to-EBIT --------------------------------
#
# Контракт: компоненты приходят на latest annual report — PBT+interest_expense
# для EBIT, equity_period_start/end для ROE, total_debt для Debt-to-EBIT.
# Все Optional; None семантика — «нет данных», не «ноль». ROE отдельно: ноль
# или отрицательный equity_avg → None (математически ROE не определён).


def _annual_extended(
    year: int,
    *,
    revenue: int = 1_000_000_000,
    net_profit: int = 100_000_000,
    profit_before_tax: int | None = 130_000_000,
    interest_expense: int | None = 20_000_000,
    equity_end: int | None = 500_000_000,
    equity_start: int | None = 450_000_000,
    total_debt_end: int | None = 200_000_000,
    total_debt_start: int | None = 180_000_000,
) -> FinancialReport:
    """Годовой отчёт с CA-037 расширениями. None — поле отсутствует в исходных."""

    def money_opt(v: int | None) -> Money | None:
        return Money(Decimal(v), UZS) if v is not None else None

    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=Money(Decimal(revenue), UZS),
        net_profit=Money(Decimal(net_profit), UZS),
        taxes_paid=Money(Decimal(revenue // 20), UZS),
        profit_before_tax=money_opt(profit_before_tax),
        interest_expense=money_opt(interest_expense),
        equity=money_opt(equity_end),
        equity_period_start=money_opt(equity_start),
        total_debt=money_opt(total_debt_end),
        total_debt_period_start=money_opt(total_debt_start),
    )


# ----------- compute_ebit ------------------------------------------------------


def test_ebit_happy_path_pbt_plus_interest() -> None:
    """EBIT = PBT + interest_expense (UZS). Знак не нормализуется — отрицательный PBT
    с большим interest даёт positive EBIT (что не red flag сам по себе, см.
    contract: Debt-to-EBIT отдельно ловит ebit <= 0)."""
    annual = _annual_extended(
        2025, profit_before_tax=130_000_000, interest_expense=20_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))

    assert bundle.ebit is not None
    assert bundle.ebit.value == Decimal("150000000")
    assert bundle.ebit.unit is KpiUnit.UZS


def test_ebit_none_when_pbt_missing() -> None:
    """PBT None → EBIT None — не выдумываем число, даже если interest есть."""
    annual = _annual_extended(2025, profit_before_tax=None, interest_expense=20_000_000)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.ebit is None


def test_ebit_none_when_interest_missing() -> None:
    annual = _annual_extended(2025, profit_before_tax=130_000_000, interest_expense=None)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.ebit is None


def test_ebit_none_when_no_annual_reports() -> None:
    bundle = compute_kpis(_snapshot())
    assert bundle.ebit is None


def test_ebit_yoy_when_prior_year_present() -> None:
    """YoY% = (current − prior) / prior × 100, на двух годовых отчётах."""
    prior = _annual_extended(2024, profit_before_tax=80_000_000, interest_expense=20_000_000)
    current = _annual_extended(2025, profit_before_tax=130_000_000, interest_expense=20_000_000)
    bundle = compute_kpis(_snapshot(annual=[prior, current]))

    # ebit_current = 150M, ebit_prior = 100M → YoY +50%
    assert bundle.ebit is not None
    assert bundle.ebit.value == Decimal("150000000")
    assert bundle.ebit.yoy_pct == Decimal(50)


# ----------- compute_roe -------------------------------------------------------


def test_roe_happy_primary_equity_avg_from_single_report() -> None:
    """primary path: equity_avg = (equity_period_start + equity) / 2 из ОДНОГО
    FORM_1 (два столбца). ROE% = net_profit_ltm / equity_avg * 100."""
    annual = _annual_extended(
        2025, net_profit=100_000_000, equity_start=400_000_000, equity_end=600_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))

    # equity_avg = (400 + 600) / 2 = 500M; ROE = 100 / 500 * 100 = 20%
    assert bundle.roe is not None
    assert bundle.roe.value == Decimal(20)
    assert bundle.roe.unit is KpiUnit.PCT


def test_roe_fallback_uses_prev_report_equity_when_start_missing() -> None:
    """Если latest.equity_period_start = None — берём prev_report.equity (end)
    как proxy для start. Согласовано CA-037 plan: fallback chain."""
    prior = _annual_extended(2024, equity_end=400_000_000)
    current = _annual_extended(
        2025,
        net_profit=120_000_000,
        equity_start=None,  # FORM_1 не дал period_start
        equity_end=600_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[prior, current]))

    # equity_avg = (prior.equity_end=400 + current.equity_end=600) / 2 = 500M
    # ROE = 120 / 500 * 100 = 24%
    assert bundle.roe is not None
    assert bundle.roe.value == Decimal(24)


def test_roe_none_when_equity_avg_zero() -> None:
    """equity_avg == 0 → деление на ноль → None (а не Infinity).
    Семантически: «нет собственного капитала» — ROE не определён."""
    annual = _annual_extended(2025, equity_start=0, equity_end=0)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.roe is None


def test_roe_none_when_equity_avg_negative() -> None:
    """Отрицательный equity_avg → None. Это red-flag сигнал
    (TODO[CA-XXX]: rule NEGATIVE_EQUITY); KPI карточка показывает empty state
    «Отрицательный собственный капитал — ROE не определён»."""
    annual = _annual_extended(2025, equity_start=-100_000_000, equity_end=-50_000_000)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.roe is None


def test_roe_none_when_no_annual_reports() -> None:
    bundle = compute_kpis(_snapshot())
    assert bundle.roe is None


def test_roe_none_when_equity_completely_missing() -> None:
    """Ни equity_end, ни equity_start, ни prev_report — посчитать avg нельзя."""
    annual = _annual_extended(2025, equity_end=None, equity_start=None)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.roe is None


# ----------- compute_debt_to_ebit ---------------------------------------------


def test_debt_to_ebit_happy_ratio_in_x_format() -> None:
    """Happy: debt = 600M, ebit = 150M → 4.0×."""
    annual = _annual_extended(
        2025,
        profit_before_tax=130_000_000,
        interest_expense=20_000_000,
        total_debt_end=600_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))

    assert bundle.debt_to_ebit is not None
    assert bundle.debt_to_ebit.value == Decimal(4)
    assert bundle.debt_to_ebit.unit is KpiUnit.RATIO


def test_debt_to_ebit_special_zero_when_no_debt() -> None:
    """total_debt = Money(0) → ratio = 0 (Decimal("0")). UI рендерит как
    «Нет долга» зелёный pill. Отличается от None (нет данных)."""
    annual = _annual_extended(2025, total_debt_end=0)
    bundle = compute_kpis(_snapshot(annual=[annual]))

    assert bundle.debt_to_ebit is not None
    assert bundle.debt_to_ebit.value == Decimal(0)


def test_debt_to_ebit_none_when_ebit_negative() -> None:
    """ebit <= 0 → None. Семантически: на убыточной компании нельзя оценить
    долговую нагрузку (нужно покрытие из прибыли, которой нет). UI рендерит
    «Долговая нагрузка не оценима (убыток)»."""
    annual = _annual_extended(
        2025,
        profit_before_tax=-30_000_000,
        interest_expense=10_000_000,  # ebit = -20M
        total_debt_end=500_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.debt_to_ebit is None


def test_debt_to_ebit_none_when_ebit_zero() -> None:
    """ebit = 0 → деление на ноль → None. Та же семантика, что и negative."""
    annual = _annual_extended(
        2025,
        profit_before_tax=-20_000_000,
        interest_expense=20_000_000,
        total_debt_end=100_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.debt_to_ebit is None


def test_debt_to_ebit_none_when_debt_missing() -> None:
    """total_debt = None → None. UI отличает от «нет долга» (Money(0)) и
    рендерит empty card «Загрузите Форму №1»."""
    annual = _annual_extended(2025, total_debt_end=None)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.debt_to_ebit is None


def test_debt_to_ebit_none_when_ebit_components_missing() -> None:
    """PBT None → EBIT None → Debt-to-EBIT None (нет знаменателя)."""
    annual = _annual_extended(
        2025, profit_before_tax=None, interest_expense=20_000_000, total_debt_end=600_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.debt_to_ebit is None


# ----------- CA-048: level_tone категоризация ---------------------------------
#
# Backend-резидентный single source of truth для absolute-level порогов
# (см. KpiBundle docstring). Boundary inclusive на верхней границе warn:
# ROE 15.00 → WARN (не GOOD), 5.00 → WARN (не BAD); Debt/EBIT 2.00 → WARN
# (не GOOD), 4.00 → WARN (не BAD).


@pytest.mark.parametrize(
    "net_profit,expected_tone",
    [
        (20_000_000, KpiLevelTone.GOOD),  # ROE = 20%
        (15_010_000, KpiLevelTone.GOOD),  # 15.01%
        (15_000_000, KpiLevelTone.WARN),  # 15.00% — boundary inclusive в warn
        (10_000_000, KpiLevelTone.WARN),  # 10%
        (5_000_000, KpiLevelTone.WARN),  # 5.00% — boundary inclusive в warn
        (4_990_000, KpiLevelTone.BAD),  # 4.99%
        (1_000_000, KpiLevelTone.BAD),  # 1%
    ],
)
def test_roe_level_tone_boundary(net_profit: int, expected_tone: KpiLevelTone) -> None:
    """ROE level_tone пороги: >15 GOOD, 5..15 WARN, <5 BAD. equity_avg фиксирован
    100M (50M start + 150M end → /2 = 100M) — варьируем net_profit, получаем
    нужный ROE через net/avg×100."""
    annual = _annual_extended(
        2025, net_profit=net_profit, equity_start=50_000_000, equity_end=150_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.roe is not None
    assert bundle.roe.level_tone is expected_tone


@pytest.mark.parametrize(
    "total_debt,expected_tone",
    [
        (150_000_000, KpiLevelTone.GOOD),  # ratio 1.5×
        (199_000_000, KpiLevelTone.GOOD),  # 1.99×
        (200_000_000, KpiLevelTone.WARN),  # 2.00× — boundary inclusive в warn
        (300_000_000, KpiLevelTone.WARN),  # 3×
        (400_000_000, KpiLevelTone.WARN),  # 4.00× — boundary inclusive в warn
        (401_000_000, KpiLevelTone.BAD),  # 4.01×
        (1_000_000_000, KpiLevelTone.BAD),  # 10×
    ],
)
def test_debt_to_ebit_level_tone_boundary(
    total_debt: int, expected_tone: KpiLevelTone,
) -> None:
    """Debt/EBIT level_tone пороги: <2 GOOD, 2..4 WARN, >4 BAD. ebit
    фиксирован 100M (PBT 80M + interest 20M) — варьируем total_debt."""
    annual = _annual_extended(
        2025,
        profit_before_tax=80_000_000,
        interest_expense=20_000_000,
        total_debt_end=total_debt,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.debt_to_ebit is not None
    assert bundle.debt_to_ebit.level_tone is expected_tone


def test_debt_to_ebit_zero_is_good_level_tone() -> None:
    """total_debt = 0 («Нет долга») → GOOD. Frontend всё равно рисует
    спец-карточку NoDebtCard, но backend-контракт консистентен (GOOD,
    не None) — пригодится для аудит-логирования."""
    annual = _annual_extended(2025, total_debt_end=0)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.debt_to_ebit is not None
    assert bundle.debt_to_ebit.level_tone is KpiLevelTone.GOOD


def test_revenue_ltm_has_no_level_tone() -> None:
    """Revenue LTM не категоризируется — нет универсального threshold для
    абсолютной выручки (зависит от отрасли/размера)."""
    bundle = compute_kpis(_snapshot(annual=[_annual(2025, 1_000_000_000)]))
    assert bundle.revenue_ltm is not None
    assert bundle.revenue_ltm.level_tone is None


def test_ebit_has_no_level_tone() -> None:
    """EBIT не категоризируется — нет универсального threshold для абсолютной
    величины. Раскраска по YoY-тренду происходит на frontend через pill."""
    annual = _annual_extended(2025, profit_before_tax=130_000_000, interest_expense=20_000_000)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.ebit is not None
    assert bundle.ebit.level_tone is None


def test_kpi_bundle_renamed_fields_replace_ebitda() -> None:
    """CA-037 контракт: KpiBundle экспортирует `ebit` / `debt_to_ebit` —
    старые имена ebitda/debt_to_ebitda удалены. Это breaking change для
    DossierViewResponseSchema (CA-037.5) и frontend (CA-037.6)."""
    bundle = compute_kpis(_snapshot())
    assert hasattr(bundle, "ebit")
    assert hasattr(bundle, "debt_to_ebit")
    assert not hasattr(bundle, "ebitda")
    assert not hasattr(bundle, "debt_to_ebitda")


# ----------- monthly_revenue_24m chart -----------------------------------------


def test_monthly_revenue_24m_returns_empty_when_no_data() -> None:
    points = compute_monthly_revenue_24m(_snapshot())
    assert points == ()


def test_monthly_revenue_24m_takes_last_24_in_chrono_order() -> None:
    """30 точек → берём последние 24, по возрастанию даты."""
    monthly = [_monthly(date(2024, m, 1), 1_000_000_000 + m) for m in range(1, 13)]
    monthly += [_monthly(date(2025, m, 1), 1_500_000_000 + m) for m in range(1, 13)]
    monthly += [_monthly(date(2026, m, 1), 2_000_000_000 + m) for m in range(1, 7)]
    # Всего 30 точек

    points = compute_monthly_revenue_24m(_snapshot(monthly=monthly))

    assert len(points) == 24
    assert points[0].month_start == date(2024, 7, 1)  # отбросили 2024-01..06
    assert points[-1].month_start == date(2026, 6, 1)


def test_monthly_revenue_24m_marks_top_3_as_peak() -> None:
    """Три самых высоких месяца помечены is_peak=True, остальные — False."""
    monthly = [_monthly(date(2025, m, 1), 1_000_000_000) for m in range(1, 10)]
    # Три ярких пика в декабре каждого года
    monthly.append(_monthly(date(2025, 10, 1), 5_000_000_000))
    monthly.append(_monthly(date(2025, 11, 1), 6_000_000_000))
    monthly.append(_monthly(date(2025, 12, 1), 7_000_000_000))

    points = compute_monthly_revenue_24m(_snapshot(monthly=monthly))

    peak_months = [p.month_start for p in points if p.is_peak]
    assert sorted(peak_months) == [date(2025, 10, 1), date(2025, 11, 1), date(2025, 12, 1)]


def test_monthly_revenue_24m_trend_is_rolling_average() -> None:
    """Тренд i-й точки = среднее последних min(12, i+1) значений."""
    monthly = [_monthly(date(2025, m, 1), m * 1_000_000) for m in range(1, 13)]

    points = compute_monthly_revenue_24m(_snapshot(monthly=monthly))

    # Для i=0 (январь, revenue=1M) тренд = среднее одной точки = 1M
    assert points[0].trend == Decimal("1000000")
    # Для i=11 (декабрь, revenue=12M) тренд = среднее [1..12] = 78/12 = 6.5M
    assert points[11].trend == Decimal("6500000")


def test_monthly_revenue_24m_filters_non_uzs() -> None:
    """USD точки выпадают из выборки."""
    monthly = [_monthly(date(2025, m, 1), 1_000_000_000) for m in range(1, 13)]
    monthly.append(_monthly(date(2026, 1, 1), 999, currency=USD))

    points = compute_monthly_revenue_24m(_snapshot(monthly=monthly))

    assert len(points) == 12  # USD точка отброшена
    assert all(p.month_start.year == 2025 for p in points)
