"""KPI-калькулятор для экрана досье (Phase 3.B / CA-037).

Pure function над ``BorrowerSnapshot``: выдаёт ``KpiBundle`` для GET
/api/dossier/{id}. Domain не зависит от этого модуля.

Что считаем (degraded-aware, правило A):
* ``revenue_ltm`` — приоритет ``monthly_turnover`` (последние 12 месяцев),
  fallback на последний ``annual_report``. Если нет ни того, ни другого →
  ``None``.
* ``ebit`` (CA-037) — последний годовой отчёт: ``profit_before_tax +
  interest_expense``. Если хотя бы одно None → KPI None. YoY% берётся с
  предыдущего годового отчёта, если у него оба компонента есть.
* ``roe`` (CA-037) — net_profit (latest annual) / equity_avg × 100, где
  ``equity_avg = (balance_start.equity + balance_end.equity) / 2`` (primary:
  единый FORM_1 даёт обе колонки), либо ``(prev.balance_end.equity +
  latest.balance_end.equity) / 2`` (fallback на end предыдущего отчёта).
  ``equity_avg ≤ 0`` → ``None`` (отрицательный SE — отдельный red-flag сигнал,
  правило NEGATIVE_EQUITY, CA-049).
* ``debt_to_ebit`` (CA-037) — 4-кейсовая state-machine: см. KpiBundle docstring.

Все деньги в snapshot — ``Money`` с ``Currency``. Здесь работаем только с
``UZS`` записями (ETL гарантирует UZS для МСБ Узбекистана; non-UZS — редкая
эксцеция, в Phase 3.B игнорируем).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from application.dto.kpi_bundle import (
    KpiBundle,
    KpiLevelTone,
    KpiUnit,
    KpiValue,
    MonthlyRevenuePoint,
)
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money


def compute_kpis(snapshot: BorrowerSnapshot) -> KpiBundle:
    """Считает KPI-набор для экрана досье. ``snapshot.as_of`` определяет
    «сейчас» — но фактически берём самые свежие данные из коллекций (адаптеры
    могут прислать данные старше as_of, и это нормально для исторического
    прогона).
    """
    annual_uzs = sorted(
        _filter_uzs_annual(snapshot.annual_reports),
        key=lambda a: a.period.start,
    )
    latest = annual_uzs[-1] if annual_uzs else None
    prior = annual_uzs[-2] if len(annual_uzs) >= 2 else None

    return KpiBundle(
        revenue_ltm=_compute_revenue_ltm(snapshot),
        ebit=_compute_ebit(latest, prior),
        roe=_compute_roe(latest, prior),
        debt_to_ebit=_compute_debt_to_ebit(latest, prior),
        # ADR-0024 (Session 1): расширенный KPI набор. Все 6 — degraded-aware
        # (None при отсутствующих компонентах); legacy ebit/debt_to_ebit
        # сохраняются рядом (CA-037 invariant).
        ebitda=_compute_ebitda(latest),
        debt_to_ebitda=_compute_debt_to_ebitda(latest),
        current_ratio=_compute_current_ratio(latest),
        working_capital=_compute_working_capital(latest),
        interest_coverage=_compute_interest_coverage(latest),
        dscr=_compute_dscr(latest, snapshot.loan_request),
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


# ----------- CA-037: EBIT / ROE / Debt-to-EBIT --------------------------------


def _money_amount(value: Money | None) -> Decimal | None:
    return value.amount if value is not None else None


def _ebit_amount(report: FinancialReport | None) -> Decimal | None:
    """EBIT-LTM компонент годового отчёта: PBT + interest_expense. Любое
    отсутствующее звено → None (контракт: «не выдумываем»). Знак сохраняется,
    отрицательный EBIT возможен (убыток покрыт большим interest — редкость,
    но математически валидно).
    """
    if report is None:
        return None
    pbt = _money_amount(report.profit_before_tax)
    interest = _money_amount(report.interest_expense)
    if pbt is None or interest is None:
        return None
    return pbt + interest


def _compute_ebit(
    latest: FinancialReport | None, prior: FinancialReport | None
) -> KpiValue | None:
    """EBIT из latest + YoY% из prior (если оба валидны)."""
    current = _ebit_amount(latest)
    if current is None:
        return None
    prior_value = _ebit_amount(prior)
    yoy_pct: Decimal | None = None
    if prior_value is not None and prior_value != 0:
        yoy_pct = (current - prior_value) / prior_value * Decimal(100)
    return KpiValue(value=current, unit=KpiUnit.UZS, yoy_pct=yoy_pct, sparkline=())


def _equity_avg(
    latest: FinancialReport, prior: FinancialReport | None
) -> Decimal | None:
    """Среднее equity между началом и концом отчётного периода.

    Primary: ``(balance_start.equity + balance_end.equity) / 2`` — единый
    FORM_1 даёт обе колонки. Fallback: ``(prior.balance_end.equity +
    latest.balance_end.equity) / 2`` — если start отсутствует, end предыдущего
    отчёта проксирует «начало» текущего периода.

    None если обе не выработаны. Знак сохраняется: отрицательный или нулевой
    avg вызывающая сторона трактует как «ROE не определён».
    """
    end = _money_amount(latest.balance_end.equity) if latest.balance_end else None
    if end is None:
        return None
    start = (
        _money_amount(latest.balance_start.equity)
        if latest.balance_start
        else None
    )
    if start is None and prior is not None and prior.balance_end is not None:
        start = _money_amount(prior.balance_end.equity)
    if start is None:
        return None
    return (start + end) / Decimal(2)


def _roe_level_tone(roe_pct: Decimal) -> KpiLevelTone:
    """CA-048 пороги ROE: >15 GOOD, 5..15 WARN, <5 BAD. Boundary inclusive
    на верхней границе warn — 15.00 и 5.00 попадают в WARN."""
    if roe_pct > Decimal(15):
        return KpiLevelTone.GOOD
    if roe_pct >= Decimal(5):
        return KpiLevelTone.WARN
    return KpiLevelTone.BAD


def _compute_roe(
    latest: FinancialReport | None, prior: FinancialReport | None
) -> KpiValue | None:
    """ROE% = net_profit_ltm / equity_avg × 100. ``equity_avg ≤ 0`` → None."""
    if latest is None:
        return None
    avg = _equity_avg(latest, prior)
    if avg is None or avg <= 0:
        return None
    net = latest.net_profit.amount
    roe_pct = net / avg * Decimal(100)
    return KpiValue(
        value=roe_pct,
        unit=KpiUnit.PCT,
        yoy_pct=None,  # CA-037: ROE YoY отложен (нужны 2 FORM_1 разных лет)
        sparkline=(),
        level_tone=_roe_level_tone(roe_pct),
    )


def _debt_to_ebit_level_tone(ratio: Decimal) -> KpiLevelTone:
    """CA-048 пороги Debt/EBIT: <2 GOOD, 2..4 WARN, >4 BAD. Boundary inclusive
    на верхней границе warn — 2.00 и 4.00 попадают в WARN. ratio == 0
    («нет долга») трактуется как GOOD."""
    if ratio < Decimal(2):
        return KpiLevelTone.GOOD
    if ratio <= Decimal(4):
        return KpiLevelTone.WARN
    return KpiLevelTone.BAD


def _compute_debt_to_ebit(
    latest: FinancialReport | None, prior: FinancialReport | None
) -> KpiValue | None:
    """4-кейсовая state machine (см. KpiBundle docstring):
    * total_debt None → None (UI: empty card «Загрузите Форму №1»);
    * total_debt = 0 → Decimal("0") (UI: «Нет долга»);
    * EBIT ≤ 0 → None (UI: «Долговая нагрузка не оценима (убыток)»);
    * иначе → Decimal ratio.
    """
    if latest is None or latest.balance_end is None:
        return None
    debt = _money_amount(latest.balance_end.total_debt)
    if debt is None:
        return None
    if debt == 0:
        return KpiValue(
            value=Decimal(0),
            unit=KpiUnit.RATIO,
            yoy_pct=None,
            sparkline=(),
            level_tone=KpiLevelTone.GOOD,
        )
    ebit = _ebit_amount(latest)
    if ebit is None or ebit <= 0:
        return None
    ratio = debt / ebit
    return KpiValue(
        value=ratio,
        unit=KpiUnit.RATIO,
        yoy_pct=None,  # CA-037: YoY отложен
        sparkline=(),
        level_tone=_debt_to_ebit_level_tone(ratio),
    )


# ----------- ADR-0024: extended KPI set ---------------------------------------
#
# 6 расширенных KPI рядом с legacy ebit/debt_to_ebit (CA-037 invariant).
# Каждая функция — pure, без I/O. Все возвращают KpiValue | None: None при
# отсутствующих компонентах или невозможной арифметике (делитель ≤ 0).
# Пороги — single source of truth здесь (CA-048); не дублировать на frontend/PDF.

# Decimal-константы для thresholds (избегаем магических чисел в коде).
_RATIO_GOOD = Decimal("1.5")
_RATIO_WARN = Decimal("1.0")
_DSCR_GOOD = Decimal("1.5")
_DSCR_WARN = Decimal("1.2")
_DEBT_EBITDA_GOOD = Decimal("3")
_DEBT_EBITDA_WARN = Decimal("5")
_IC_GOOD = Decimal("3")
_IC_WARN = Decimal("1.5")
# DSCR principal annualization: same формула что в domain/rules/financial/dscr_low.py.
_DSCR_MONTHS_IN_YEAR = Decimal("12")


def _ebitda_amount(report: FinancialReport | None) -> Decimal | None:
    """EBITDA = PBT + interest_expense + D&A. Любой компонент None → None.

    В отличие от _ebit_amount (CA-037) добавляем depreciation_amortization
    из ADR-0024. D&A отсутствует во многих snapshot'ах — парсер FORM_2 пока
    не извлекает поле — fallback на EBIT здесь намеренно НЕ делаем: пользователь
    должен явно видеть «нет D&A → нет EBITDA», иначе EBITDA вырождается в
    дубликат EBIT.
    """
    if report is None:
        return None
    pbt = _money_amount(report.profit_before_tax)
    interest = _money_amount(report.interest_expense)
    da = _money_amount(report.depreciation_amortization)
    if pbt is None or interest is None or da is None:
        return None
    return pbt + interest + da


def _compute_ebitda(latest: FinancialReport | None) -> KpiValue | None:
    """EBITDA из latest_annual. Знак сохраняется, отрицательная EBITDA валидна
    (убыток покрыт большим interest+D&A — редкость, но математически возможно).
    """
    amount = _ebitda_amount(latest)
    if amount is None:
        return None
    return KpiValue(value=amount, unit=KpiUnit.UZS, yoy_pct=None, sparkline=())


def _debt_to_ebitda_level_tone(ratio: Decimal) -> KpiLevelTone:
    """Пороги Debt/EBITDA: <3 GOOD, 3..5 WARN, >5 BAD. Boundary inclusive на
    верхней границе warn — 3.00 и 5.00 → WARN. ratio == 0 («нет долга») → GOOD.
    """
    if ratio < _DEBT_EBITDA_GOOD:
        return KpiLevelTone.GOOD
    if ratio <= _DEBT_EBITDA_WARN:
        return KpiLevelTone.WARN
    return KpiLevelTone.BAD


def _compute_debt_to_ebitda(latest: FinancialReport | None) -> KpiValue | None:
    """Debt / EBITDA. 4-кейсовая state-machine, аналог _compute_debt_to_ebit:
    * total_debt None → None;
    * total_debt = 0 → Decimal("0"), GOOD;
    * EBITDA None или ≤ 0 → None (убыток или нет D&A);
    * иначе → ratio.
    """
    if latest is None or latest.balance_end is None:
        return None
    debt = _money_amount(latest.balance_end.total_debt)
    if debt is None:
        return None
    if debt == 0:
        return KpiValue(
            value=Decimal(0),
            unit=KpiUnit.RATIO,
            yoy_pct=None,
            sparkline=(),
            level_tone=KpiLevelTone.GOOD,
        )
    ebitda = _ebitda_amount(latest)
    if ebitda is None or ebitda <= 0:
        return None
    ratio = debt / ebitda
    return KpiValue(
        value=ratio,
        unit=KpiUnit.RATIO,
        yoy_pct=None,
        sparkline=(),
        level_tone=_debt_to_ebitda_level_tone(ratio),
    )


def _current_ratio_level_tone(ratio: Decimal) -> KpiLevelTone:
    """Пороги Current Ratio: >1.5 GOOD, 1.0..1.5 WARN, <1.0 BAD. Boundary
    inclusive: 1.00 и 1.50 → WARN.
    """
    if ratio > _RATIO_GOOD:
        return KpiLevelTone.GOOD
    if ratio >= _RATIO_WARN:
        return KpiLevelTone.WARN
    return KpiLevelTone.BAD


def _compute_current_ratio(latest: FinancialReport | None) -> KpiValue | None:
    """Current Ratio = CA / CL. ``CL ≤ 0`` → None (нет краткосрочных
    обязательств — ratio неопределим)."""
    if latest is None or latest.balance_end is None:
        return None
    ca = _money_amount(latest.balance_end.current_assets)
    cl = _money_amount(latest.balance_end.current_liabilities)
    if ca is None or cl is None:
        return None
    if cl <= 0:
        return None
    ratio = ca / cl
    return KpiValue(
        value=ratio,
        unit=KpiUnit.RATIO,
        yoy_pct=None,
        sparkline=(),
        level_tone=_current_ratio_level_tone(ratio),
    )


def _compute_working_capital(latest: FinancialReport | None) -> KpiValue | None:
    """Working Capital = CA − CL. Money-KPI; level_tone=None (нет universal
    threshold — отрицательный WC может быть OK для retail с быстрым cash cycle).
    UI показывает знак через cdr/changeTone, не через GOOD/WARN/BAD stripe.
    """
    if latest is None or latest.balance_end is None:
        return None
    ca = _money_amount(latest.balance_end.current_assets)
    cl = _money_amount(latest.balance_end.current_liabilities)
    if ca is None or cl is None:
        return None
    return KpiValue(
        value=ca - cl, unit=KpiUnit.UZS, yoy_pct=None, sparkline=(),
    )


def _interest_coverage_level_tone(ratio: Decimal) -> KpiLevelTone:
    """Пороги Interest Coverage: >3 GOOD, 1.5..3 WARN, <1.5 BAD. Boundary
    inclusive: 1.50 и 3.00 → WARN.
    """
    if ratio > _IC_GOOD:
        return KpiLevelTone.GOOD
    if ratio >= _IC_WARN:
        return KpiLevelTone.WARN
    return KpiLevelTone.BAD


def _compute_interest_coverage(latest: FinancialReport | None) -> KpiValue | None:
    """Interest Coverage = EBIT / interest_expense.
    * interest_expense ≤ 0 → None («нет процентных расходов → ratio не нужен»);
    * EBIT None → None;
    * EBIT ≤ 0 → возвращаем отрицательный ratio с tone BAD (банк видит «не
      покрывает» вместо «нет данных»).
    """
    if latest is None:
        return None
    interest = _money_amount(latest.interest_expense)
    if interest is None or interest <= 0:
        return None
    ebit = _ebit_amount(latest)
    if ebit is None:
        return None
    ratio = ebit / interest
    return KpiValue(
        value=ratio,
        unit=KpiUnit.RATIO,
        yoy_pct=None,
        sparkline=(),
        level_tone=_interest_coverage_level_tone(ratio),
    )


def _dscr_level_tone(ratio: Decimal) -> KpiLevelTone:
    """Пороги DSCR: >1.5 GOOD, 1.2..1.5 WARN, <1.2 BAD. Murodov O.J. 2025
    эмпирический минимум 1.3; IFC SME ch.4 minimum 1.25 + comfort 1.5. Boundary
    inclusive: 1.20 и 1.50 → WARN.
    """
    if ratio > _DSCR_GOOD:
        return KpiLevelTone.GOOD
    if ratio >= _DSCR_WARN:
        return KpiLevelTone.WARN
    return KpiLevelTone.BAD


def _compute_dscr(
    latest: FinancialReport | None,
    loan_request: LoanRequest | None,
) -> KpiValue | None:
    """DSCR = numerator / annual_debt_service.

    Numerator fallback chain (same контракт что в domain/rules/financial/dscr_low.py):
    OCF → EBITDA → EBIT. Если ни один не доступен → None.

    Знаменатель: ``interest_expense + (loan_amount × 12 / term_months)`` —
    annualized principal (linear approx, без амортизационного графика).
    Без loan_request — нечем считать debt service, → None. С term_months=0
    или loan_amount≤0 → None (Pydantic уже валидирует, guard на всякий случай).

    Формула продублирована (без shared helper) — KPI и rule живут в разных
    слоях с разными контрактами (display vs fire/silent). 5 строк дубля
    accepted, см. plan-doc Risks.
    """
    if latest is None or loan_request is None:
        return None
    if loan_request.term_months <= 0:
        return None
    loan_amount = loan_request.amount.amount
    if loan_amount <= 0:
        return None
    interest = _money_amount(latest.interest_expense)
    if interest is None:
        return None

    if latest.operating_cash_flow is not None:
        numerator = latest.operating_cash_flow.amount
    elif (
        latest.profit_before_tax is not None
        and latest.depreciation_amortization is not None
    ):
        numerator = (
            latest.profit_before_tax.amount + interest + latest.depreciation_amortization.amount
        )
    elif latest.profit_before_tax is not None:
        numerator = latest.profit_before_tax.amount + interest
    else:
        return None

    principal_annual = loan_amount * _DSCR_MONTHS_IN_YEAR / Decimal(loan_request.term_months)
    debt_service = interest + principal_annual
    if debt_service <= 0:
        return None

    ratio = numerator / debt_service
    return KpiValue(
        value=ratio,
        unit=KpiUnit.RATIO,
        yoy_pct=None,
        sparkline=(),
        level_tone=_dscr_level_tone(ratio),
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
