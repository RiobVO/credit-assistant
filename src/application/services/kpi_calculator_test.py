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
from domain.value_objects.balance_snapshot import BalanceSnapshot
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
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
        oked_main="62.01",
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
    # ADR-0024 (Session 1): новые опциональные поля под расширенный KPI набор.
    # Defaults None — старые тесты не аффектятся (новые KPI просто возвращают None).
    depreciation_amortization: int | None = None,
    operating_cash_flow: int | None = None,
    current_assets_end: int | None = None,
    current_liabilities_end: int | None = None,
    # ADR-0024 (Session 2): inventory под Quick Ratio.
    inventory_end: int | None = None,
    # ADR-0024 (Session 4): total liabilities + FX-компонент под
    # fx_exposure_ratio. liabilities_end отделён от total_debt_end (debt — это
    # долговые обязательства, liabilities — все обязательства).
    liabilities_end: int | None = None,
    liabilities_fx_end: int | None = None,
) -> FinancialReport:
    """Годовой отчёт с CA-037 расширениями + ADR-0024 (Session 1) полями.
    None — поле отсутствует в исходных.

    CA-047: balance_end / balance_start как BalanceSnapshot sub-entity;
    пустой snapshot (`is_empty()=True`) превращается в None — KPI calculator
    обрабатывает это как «FORM_1 не загружен».
    """

    def money_opt(v: int | None) -> Money | None:
        return Money(Decimal(v), UZS) if v is not None else None

    balance_end = BalanceSnapshot(
        equity=money_opt(equity_end),
        total_debt=money_opt(total_debt_end),
        current_assets=money_opt(current_assets_end),
        current_liabilities=money_opt(current_liabilities_end),
        inventory=money_opt(inventory_end),
        liabilities=money_opt(liabilities_end),
        liabilities_fx=money_opt(liabilities_fx_end),
    )
    balance_start = BalanceSnapshot(
        equity=money_opt(equity_start), total_debt=money_opt(total_debt_start),
    )

    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=Money(Decimal(revenue), UZS),
        net_profit=Money(Decimal(net_profit), UZS),
        taxes_paid=Money(Decimal(revenue // 20), UZS),
        profit_before_tax=money_opt(profit_before_tax),
        interest_expense=money_opt(interest_expense),
        depreciation_amortization=money_opt(depreciation_amortization),
        operating_cash_flow=money_opt(operating_cash_flow),
        balance_end=balance_end if not balance_end.is_empty() else None,
        balance_start=balance_start if not balance_start.is_empty() else None,
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


def test_kpi_bundle_legacy_and_extended_coexist() -> None:
    """CA-037 invariant + ADR-0024: legacy ``ebit`` / ``debt_to_ebit`` и
    расширенные ``ebitda`` / ``debt_to_ebitda`` живут **рядом** — не
    переименовываем после появления D&A. UI/PDF показывают и то, и другое
    отдельными карточками."""
    bundle = compute_kpis(_snapshot())
    # CA-037: legacy пара осталась.
    assert hasattr(bundle, "ebit")
    assert hasattr(bundle, "debt_to_ebit")
    # ADR-0024 (Session 1): расширенная шестёрка добавлена.
    for field in (
        "ebitda",
        "debt_to_ebitda",
        "current_ratio",
        "working_capital",
        "interest_coverage",
        "dscr",
    ):
        assert hasattr(bundle, field), f"KpiBundle missing field {field!r}"


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


# ============================================================================
# ADR-0024 (Session 1): EBITDA / debt_to_ebitda / current_ratio /
# working_capital / interest_coverage / DSCR
# ============================================================================
#
# Контракт: 6 расширенных KPI рядом с legacy ebit/debt_to_ebit. Каждое поле
# nullable: отсутствует компонент или невозможная арифметика → None.
# Пороги — single source of truth в kpi_calculator (CA-048).


def _loan_uzs(amount: int, term_months: int = 12) -> LoanRequest:
    return LoanRequest(
        amount=Money(Decimal(amount), UZS),
        term_months=term_months,
        rate_pct=Decimal("24.0"),
        purpose="working_capital",
        category="msb",
    )


def _snapshot_with_loan(
    annual: list[FinancialReport],
    loan: LoanRequest | None = None,
) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 8),
        annual_reports=annual,
        loan_request=loan,
    )


# ----------- EBITDA -----------------------------------------------------------


def test_ebitda_fires_when_pbt_interest_da_present() -> None:
    """EBITDA = PBT + interest_expense + D&A. Все компоненты заданы → значение."""
    annual = _annual_extended(
        2025,
        profit_before_tax=130_000_000,
        interest_expense=20_000_000,
        depreciation_amortization=50_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.ebitda is not None
    assert bundle.ebitda.value == Decimal("200000000")
    assert bundle.ebitda.unit is KpiUnit.UZS
    # EBITDA — absolute UZS, без universal threshold.
    assert bundle.ebitda.level_tone is None


def test_ebitda_none_when_da_missing() -> None:
    """D&A None → EBITDA None (НЕ fallback на EBIT — иначе дубликат EBIT)."""
    annual = _annual_extended(
        2025,
        profit_before_tax=130_000_000,
        interest_expense=20_000_000,
        depreciation_amortization=None,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.ebitda is None
    # EBIT при этом всё равно посчитан — две карточки независимы.
    assert bundle.ebit is not None


def test_ebitda_negative_is_valid_signed() -> None:
    """Знак сохраняется: PBT убыточен, D&A малая → отрицательная EBITDA.
    KPI это валидное состояние, debt_to_ebitda тогда дополнительно сигналит None.
    """
    annual = _annual_extended(
        2025,
        profit_before_tax=-100_000_000,
        interest_expense=10_000_000,
        depreciation_amortization=5_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.ebitda is not None
    assert bundle.ebitda.value == Decimal("-85000000")


# ----------- debt_to_ebitda ---------------------------------------------------


def test_debt_to_ebitda_fires_with_level_tone() -> None:
    """Happy: debt = 800M, EBITDA = 200M → 4.0× → WARN (3..5)."""
    annual = _annual_extended(
        2025,
        profit_before_tax=130_000_000,
        interest_expense=20_000_000,
        depreciation_amortization=50_000_000,
        total_debt_end=800_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.debt_to_ebitda is not None
    assert bundle.debt_to_ebitda.value == Decimal(4)
    assert bundle.debt_to_ebitda.level_tone is KpiLevelTone.WARN


def test_debt_to_ebitda_zero_debt_returns_zero_good() -> None:
    """total_debt = 0 → Decimal(0), tone GOOD. EBITDA не требуется (даже если
    D&A None — это «нет долга» сигнал, важнее EBITDA-неопределённости)."""
    annual = _annual_extended(
        2025,
        total_debt_end=0,
        depreciation_amortization=None,  # EBITDA сама была бы None
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.debt_to_ebitda is not None
    assert bundle.debt_to_ebitda.value == Decimal(0)
    assert bundle.debt_to_ebitda.level_tone is KpiLevelTone.GOOD


def test_debt_to_ebitda_none_when_ebitda_nonpositive() -> None:
    """EBITDA ≤ 0 → debt_to_ebitda None (нельзя оценить нагрузку при убытке)."""
    annual = _annual_extended(
        2025,
        profit_before_tax=-200_000_000,
        interest_expense=10_000_000,
        depreciation_amortization=5_000_000,  # EBITDA = -185M
        total_debt_end=500_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.debt_to_ebitda is None


# ----------- current_ratio ----------------------------------------------------


@pytest.mark.parametrize(
    "ca,cl,expected_value,expected_tone",
    [
        (3_000_000, 1_000_000, Decimal(3), KpiLevelTone.GOOD),  # 3.0 > 1.5
        (1_510_000, 1_000_000, Decimal("1.51"), KpiLevelTone.GOOD),  # 1.51 > 1.5
        (1_500_000, 1_000_000, Decimal("1.5"), KpiLevelTone.WARN),  # 1.50 boundary
        (1_200_000, 1_000_000, Decimal("1.2"), KpiLevelTone.WARN),
        (1_000_000, 1_000_000, Decimal(1), KpiLevelTone.WARN),  # 1.00 boundary
        (990_000, 1_000_000, Decimal("0.99"), KpiLevelTone.BAD),
    ],
)
def test_current_ratio_level_tone_boundary(
    ca: int, cl: int, expected_value: Decimal, expected_tone: KpiLevelTone,
) -> None:
    """Current Ratio пороги: >1.5 GOOD, 1.0..1.5 WARN, <1.0 BAD. Boundary
    inclusive — 1.50 и 1.00 → WARN."""
    annual = _annual_extended(
        2025, current_assets_end=ca, current_liabilities_end=cl,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.current_ratio is not None
    assert bundle.current_ratio.value == expected_value
    assert bundle.current_ratio.level_tone is expected_tone


def test_current_ratio_none_when_components_missing() -> None:
    """CA или CL None → None. Парсер FORM_1 пока не извлекает поля,
    snapshot почти всегда без них до manual-input."""
    annual = _annual_extended(2025)  # current_* defaults to None
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.current_ratio is None


def test_current_ratio_none_when_cl_zero() -> None:
    """CL ≤ 0 → None (ratio неопределим)."""
    annual = _annual_extended(
        2025, current_assets_end=1_000_000, current_liabilities_end=0,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.current_ratio is None


# ----------- working_capital --------------------------------------------------


def test_working_capital_positive_sign() -> None:
    """WC = CA − CL. Положительный → UZS Money. level_tone=None (Money-KPI)."""
    annual = _annual_extended(
        2025,
        current_assets_end=3_000_000_000,
        current_liabilities_end=1_000_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.working_capital is not None
    assert bundle.working_capital.value == Decimal("2000000000")
    assert bundle.working_capital.unit is KpiUnit.UZS
    assert bundle.working_capital.level_tone is None


def test_working_capital_negative_is_valid() -> None:
    """Отрицательный WC валиден — может быть OK для retail с быстрым cash cycle.
    Знак не превращается в BAD — нет universal threshold."""
    annual = _annual_extended(
        2025,
        current_assets_end=500_000_000,
        current_liabilities_end=1_000_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.working_capital is not None
    assert bundle.working_capital.value == Decimal("-500000000")
    assert bundle.working_capital.level_tone is None


def test_working_capital_none_when_components_missing() -> None:
    """CA или CL None → None (нет вычитания без обоих)."""
    annual = _annual_extended(2025)  # defaults None
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.working_capital is None


# ----------- quick_ratio (ADR-0024 Session 2) ---------------------------------


@pytest.mark.parametrize(
    "ca,inv,cl,expected_value,expected_tone",
    [
        # Quick Ratio = (CA − inventory) / CL. >1.0 GOOD / 0.7..1.0 WARN / <0.7 BAD.
        (3_000_000, 500_000, 1_000_000, Decimal("2.5"), KpiLevelTone.GOOD),
        (1_500_000, 400_000, 1_000_000, Decimal("1.1"), KpiLevelTone.GOOD),
        # Boundary 1.00 → WARN.
        (1_500_000, 500_000, 1_000_000, Decimal(1), KpiLevelTone.WARN),
        (1_200_000, 300_000, 1_000_000, Decimal("0.9"), KpiLevelTone.WARN),
        # Boundary 0.70 → WARN.
        (1_000_000, 300_000, 1_000_000, Decimal("0.7"), KpiLevelTone.WARN),
        (1_000_000, 400_000, 1_000_000, Decimal("0.6"), KpiLevelTone.BAD),
    ],
)
def test_quick_ratio_level_tone_boundary(
    ca: int,
    inv: int,
    cl: int,
    expected_value: Decimal,
    expected_tone: KpiLevelTone,
) -> None:
    """Quick Ratio пороги: >1.0 GOOD, 0.7..1.0 WARN, <0.7 BAD. Boundary
    inclusive — 0.70 и 1.00 → WARN. Source: IFC SME Knowledge Guide ch.4."""
    annual = _annual_extended(
        2025,
        current_assets_end=ca,
        current_liabilities_end=cl,
        inventory_end=inv,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.quick_ratio is not None
    assert bundle.quick_ratio.value == expected_value
    assert bundle.quick_ratio.level_tone is expected_tone
    assert bundle.quick_ratio.unit is KpiUnit.RATIO


def test_quick_ratio_silent_when_inventory_missing() -> None:
    """inventory None → quick_ratio None. Не предполагаем inventory=0 — это
    дало бы false-GOOD для retail без inventory FORM_1 загрузки."""
    annual = _annual_extended(
        2025,
        current_assets_end=1_500_000,
        current_liabilities_end=1_000_000,
        # inventory_end остаётся None
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.quick_ratio is None
    # Current Ratio тем временем определён — он не требует inventory.
    assert bundle.current_ratio is not None


def test_quick_ratio_silent_when_current_assets_missing() -> None:
    """current_assets None → quick_ratio None."""
    annual = _annual_extended(2025, inventory_end=200_000)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.quick_ratio is None


def test_quick_ratio_silent_when_cl_zero() -> None:
    """CL ≤ 0 → None (ratio неопределим, как Current Ratio)."""
    annual = _annual_extended(
        2025,
        current_assets_end=1_500_000,
        current_liabilities_end=0,
        inventory_end=200_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.quick_ratio is None


# ----------- fx_exposure_ratio (ADR-0024 Session 4) ---------------------------


def test_fx_exposure_ratio_computed_when_both_present() -> None:
    """liabilities_fx / liabilities × 100 → ratio в PCT (consistent с ROE)."""
    annual = _annual_extended(
        2025,
        liabilities_end=2_000_000_000,
        liabilities_fx_end=800_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.fx_exposure_ratio is not None
    # 800M / 2000M = 0.40 → 40 в PCT scale (ratio × 100, как ROE).
    assert bundle.fx_exposure_ratio.value == Decimal(40)
    assert bundle.fx_exposure_ratio.unit is KpiUnit.PCT
    # БЕЗ level_tone в v1: пороги ЦБ РУз отложены.
    assert bundle.fx_exposure_ratio.level_tone is None


def test_fx_exposure_ratio_silent_when_fx_missing() -> None:
    """liabilities_fx None → KPI None (banker не вводил FX-component)."""
    annual = _annual_extended(2025, liabilities_end=2_000_000_000)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.fx_exposure_ratio is None


def test_fx_exposure_ratio_silent_when_liabilities_missing() -> None:
    """liabilities None → KPI None (нечего соотносить — FORM_1 не загружен)."""
    annual = _annual_extended(2025, liabilities_fx_end=800_000_000)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.fx_exposure_ratio is None


def test_fx_exposure_ratio_silent_when_liabilities_zero() -> None:
    """liabilities = 0 → KPI None (защита от деления на ноль)."""
    annual = _annual_extended(
        2025,
        liabilities_end=0,
        liabilities_fx_end=0,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.fx_exposure_ratio is None


def test_fx_exposure_ratio_no_cap_above_100pct() -> None:
    """Edge case: liabilities_fx > liabilities (banker error) → ratio > 100%
    без cap. fmt_pct отрендерит честно «150%» — banker увидит абсурд и
    поймёт что данные неверны. Acceptable UX для v1 manual-input.
    """
    annual = _annual_extended(
        2025,
        liabilities_end=2_000_000_000,
        liabilities_fx_end=3_000_000_000,
    )
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.fx_exposure_ratio is not None
    # 3B / 2B × 100 = 150
    assert bundle.fx_exposure_ratio.value == Decimal(150)
    assert bundle.fx_exposure_ratio.unit is KpiUnit.PCT


# ----------- interest_coverage ------------------------------------------------


@pytest.mark.parametrize(
    "pbt,interest,expected_tone",
    [
        # EBIT = PBT + interest. ratio = EBIT / interest.
        (280_000_000, 20_000_000, KpiLevelTone.GOOD),  # ebit=300, ratio=15
        (41_000_000, 20_000_000, KpiLevelTone.GOOD),  # ebit=61, ratio=3.05
        (40_000_000, 20_000_000, KpiLevelTone.WARN),  # ebit=60, ratio=3.0 (bndry)
        (10_000_000, 20_000_000, KpiLevelTone.WARN),  # ebit=30, ratio=1.5 (bndry)
        (5_000_000, 20_000_000, KpiLevelTone.BAD),  # ebit=25, ratio=1.25
        (0, 20_000_000, KpiLevelTone.BAD),  # ebit=20, ratio=1.0
    ],
)
def test_interest_coverage_level_tone(
    pbt: int, interest: int, expected_tone: KpiLevelTone,
) -> None:
    """Interest Coverage = EBIT/Interest. Пороги: >3 GOOD, 1.5..3 WARN, <1.5 BAD.
    Boundary inclusive — 3.00 и 1.50 → WARN."""
    annual = _annual_extended(2025, profit_before_tax=pbt, interest_expense=interest)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.interest_coverage is not None
    assert bundle.interest_coverage.level_tone is expected_tone


def test_interest_coverage_none_when_interest_zero() -> None:
    """interest = 0 → ratio неопределим, None. Семантически: «нет процентных
    расходов» — coverage не нужен."""
    annual = _annual_extended(2025, profit_before_tax=100_000_000, interest_expense=0)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    assert bundle.interest_coverage is None


def test_interest_coverage_negative_ratio_when_ebit_negative() -> None:
    """EBIT отрицательный → отрицательный ratio с tone BAD. Банк видит «не
    покрывает» вместо «нет данных»."""
    annual = _annual_extended(2025, profit_before_tax=-30_000_000, interest_expense=10_000_000)
    bundle = compute_kpis(_snapshot(annual=[annual]))
    # ebit = -30+10 = -20; ratio = -20/10 = -2
    assert bundle.interest_coverage is not None
    assert bundle.interest_coverage.value == Decimal(-2)
    assert bundle.interest_coverage.level_tone is KpiLevelTone.BAD


# ----------- DSCR -------------------------------------------------------------


def test_dscr_ocf_path_fires_with_tone() -> None:
    """OCF доступен → числитель OCF. DSCR = 200M / (20M + 100M loan/12*12 = 20M + 100M) = 200/120
    ≈ 1.67 → GOOD (>1.5)."""
    annual = _annual_extended(
        2025,
        operating_cash_flow=200_000_000,
        interest_expense=20_000_000,
        profit_before_tax=100_000_000,
        depreciation_amortization=50_000_000,
    )
    loan = _loan_uzs(amount=100_000_000, term_months=12)
    bundle = compute_kpis(_snapshot_with_loan(annual=[annual], loan=loan))
    # principal_annual = 100M * 12 / 12 = 100M; debt_service = 20 + 100 = 120M
    # numerator OCF = 200M; ratio = 200/120 = 1.666...
    assert bundle.dscr is not None
    expected = Decimal("200000000") / Decimal("120000000")
    assert bundle.dscr.value == expected
    assert bundle.dscr.level_tone is KpiLevelTone.GOOD


def test_dscr_fallback_to_ebitda_when_no_ocf() -> None:
    """OCF None, D&A+PBT есть → numerator EBITDA. DSCR через fallback chain."""
    annual = _annual_extended(
        2025,
        operating_cash_flow=None,
        interest_expense=20_000_000,
        profit_before_tax=100_000_000,
        depreciation_amortization=50_000_000,
    )
    loan = _loan_uzs(amount=100_000_000, term_months=12)
    bundle = compute_kpis(_snapshot_with_loan(annual=[annual], loan=loan))
    # EBITDA = 100 + 20 + 50 = 170M; debt_service = 120M; ratio = 170/120 ≈ 1.42 → WARN
    assert bundle.dscr is not None
    expected = Decimal("170000000") / Decimal("120000000")
    assert bundle.dscr.value == expected
    assert bundle.dscr.level_tone is KpiLevelTone.WARN


def test_dscr_none_without_loan_request() -> None:
    """Нет loan_request → нечем считать debt_service → None. (KPI рассчитан
    только когда есть заявка — иначе нет знаменателя.)"""
    annual = _annual_extended(
        2025,
        operating_cash_flow=200_000_000,
        interest_expense=20_000_000,
    )
    bundle = compute_kpis(_snapshot_with_loan(annual=[annual], loan=None))
    assert bundle.dscr is None
