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

from application.dto.kpi_bundle import KpiUnit
from application.services.kpi_calculator import compute_kpis
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


# ----------- secondary KPIs always degraded in Phase 3.B -----------------------


def test_secondary_kpis_always_none_in_phase_3b() -> None:
    """EBITDA / ROE / Debt-to-EBITDA всегда None — нужны компоненты, которых
    нет в snapshot. Подтверждение, что мы НЕ выдумываем числа."""
    monthly = [_monthly(date(2025, m, 1), 1_000_000_000) for m in range(1, 13)]
    bundle = compute_kpis(_snapshot(monthly=monthly))

    assert bundle.ebitda is None
    assert bundle.roe is None
    assert bundle.debt_to_ebitda is None
