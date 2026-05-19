"""Tests для ConfidenceLayer (ADR-0024 / Commit 2).

5 test scenarios — соответствуют Claude research Q1 deliverable.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.entities.vat_period_report import VatPeriodReport
from domain.services.confidence_layer import (
    ConfidenceTier,
    compute_confidence,
)
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money


def _money(amount: int) -> Money:
    return Money(Decimal(amount), Currency.UZS)


def _full_borrower() -> Borrower:
    return Borrower(
        inn=INN("306399449"),
        name="ООО Тест",
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 1, 1),
        director_name="И.И.",
        director_appointed_at=date(2018, 1, 1),
        okved_main="46.39",
        registered_address="г. Ташкент",
    )


def _annual(year: int, revenue: int, profit: int) -> FinancialReport:
    return FinancialReport(
        period=DateRange(start=date(year, 1, 1), end=date(year, 12, 31)),
        revenue=_money(revenue),
        net_profit=_money(profit),
        taxes_paid=_money(0),
    )


def _monthly(year: int, month: int, revenue: int) -> MonthlyTurnover:
    return MonthlyTurnover(
        month_start=date(year, month, 1),
        revenue=_money(revenue),
    )


def _vat_period(year: int, month: int) -> VatPeriodReport:
    return VatPeriodReport(
        period=DateRange(start=date(year, month, 1), end=date(year, month, 28)),
        vat_declared=_money(1_000_000),
        esf_seller_vat_total=_money(1_000_000),
    )


def _tax_event(year: int, month: int) -> TaxEvent:
    return TaxEvent(
        date=date(year, month, 1),
        type=TaxEventType.PAYMENT,
        amount=_money(1_000_000),
        delay_days=0,
    )


def _loan() -> LoanRequest:
    return LoanRequest(
        amount=_money(100_000_000),
        term_months=12,
        rate_pct=Decimal("24.5"),
        purpose="working_capital",
        category="business",
    )


# ───────── Scenario 1: Healthy full data ────────────────────────────────


def test_scenario_1_healthy_full_data() -> None:
    """S1 (per Claude Q1): все источники заполнены → HIGH confidence, no floor."""
    snap = BorrowerSnapshot(
        borrower=_full_borrower(),
        as_of=date(2026, 5, 1),
        annual_reports=[
            _annual(2023, 14_820_000_000, 1_185_000_000),
            _annual(2024, 17_640_000_000, 1_590_000_000),
        ],
        quarterly_reports=[
            _annual(y, 1_000_000_000, 100_000_000)
            for y in range(2024, 2026)
            for _ in range(2)
        ],
        monthly_turnover=[_monthly(2025, m, 1_000_000_000) for m in range(1, 13)],
        vat_periods=[_vat_period(2025, m) for m in range(1, 7)],
        tax_events=[_tax_event(2025, m) for m in range(1, 7)],
        counterparties_buyers=[],
        counterparties_suppliers=[],
        loan_request=_loan(),
    )
    # Add buyers/suppliers using factory.
    from domain.entities.counterparty import Counterparty

    snap.counterparties_buyers.append(
        Counterparty(inn=INN("100100100"), name="Buyer1", registration_date=date(2020, 1, 1))
    )
    snap.counterparties_suppliers.append(
        Counterparty(inn=INN("200200200"), name="Supplier1", registration_date=date(2020, 1, 1))
    )

    result = compute_confidence(snap)
    assert result.tier == ConfidenceTier.HIGH
    assert result.coverage_pct >= 75


# ───────── Scenario 2: BR-2026-0050 partial (THE problem case) ────────────


def test_scenario_2_partial_borrower_with_annual_only() -> None:
    """S2 (THE bug case): borrower + 2 annual reports, всё остальное пусто.

    Это репро BR-2026-0050 TEST — раньше получал score 100 «Одобрить»
    (0 правил сработало). После Confidence Layer: tier LOW → floor 50, REVIEW.
    """
    snap = BorrowerSnapshot(
        borrower=_full_borrower(),
        as_of=date(2026, 5, 1),
        annual_reports=[
            _annual(2024, 4_435_000_000, 161_000_000),
            _annual(2025, 4_148_000_000, 360_000_000),
        ],
        loan_request=_loan(),
    )
    result = compute_confidence(snap)
    # base 10 + core 10 + annual 15 + loan 5 = 40 → LOW tier
    assert result.tier == ConfidenceTier.LOW
    assert 30 <= result.coverage_pct < 50
    assert "vat_periods" in result.sources_missing
    assert "counterparties" in result.sources_missing


# ───────── Scenario 3: Minimal data — only borrower core ────────────


def test_scenario_3_critical_only_borrower_core() -> None:
    """S3: только borrower-карточка — CRITICAL tier."""
    snap = BorrowerSnapshot(
        borrower=_full_borrower(),
        as_of=date(2026, 5, 1),
    )
    result = compute_confidence(snap)
    # base 10 + core 10 = 20 → CRITICAL
    assert result.tier == ConfidenceTier.CRITICAL
    assert result.coverage_pct < 30


# ───────── Scenario 4: Medium — half of sources ─────────────────────


def test_scenario_4_medium_half_sources() -> None:
    """S4: core + annual + VAT + monthly partial → MEDIUM tier."""
    snap = BorrowerSnapshot(
        borrower=_full_borrower(),
        as_of=date(2026, 5, 1),
        annual_reports=[
            _annual(2024, 14_000_000_000, 1_100_000_000),
            _annual(2025, 17_000_000_000, 1_500_000_000),
        ],
        vat_periods=[_vat_period(2025, m) for m in range(1, 7)],
        monthly_turnover=[_monthly(2025, m, 1_000_000_000) for m in range(1, 7)],
        loan_request=_loan(),
    )
    result = compute_confidence(snap)
    # base 10 + core 10 + annual 15 + vat 12 + monthly 10/2 ≈ 5 + loan 5 = 57 → MEDIUM
    assert result.tier == ConfidenceTier.MEDIUM
    assert 50 <= result.coverage_pct < 75


# ───────── Scenario 5: Borrower core empty (edge) ───────────────────


def test_scenario_5_borrower_core_partial_lowers_coverage() -> None:
    """S5 edge: borrower с минимальным core (только ИНН и ОПФ) → меньше coverage.

    Конкретно для проверки что partial-core засчитывается частично.
    """
    borrower = Borrower(
        inn=INN("306399449"),
        name="ООО Тест",
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 1, 1),
        director_name="",  # пусто
        director_appointed_at=date(2018, 1, 1),
        okved_main="",  # пусто
        registered_address="г. Ташкент",
    )
    snap = BorrowerSnapshot(borrower=borrower, as_of=date(2026, 5, 1))
    result = compute_confidence(snap)
    # base 10 + core_partial 2/4 (т.е. 5) = 15 → CRITICAL
    assert result.tier == ConfidenceTier.CRITICAL


# ───────── Bonus tests for tier boundaries ───────────────────────────


def test_tier_boundary_high_at_75() -> None:
    from domain.services.confidence_layer import _resolve_tier

    assert _resolve_tier(75) == ConfidenceTier.HIGH
    assert _resolve_tier(74) == ConfidenceTier.MEDIUM


def test_tier_boundary_medium_at_50() -> None:
    from domain.services.confidence_layer import _resolve_tier

    assert _resolve_tier(50) == ConfidenceTier.MEDIUM
    assert _resolve_tier(49) == ConfidenceTier.LOW


def test_tier_boundary_low_at_30() -> None:
    from domain.services.confidence_layer import _resolve_tier

    assert _resolve_tier(30) == ConfidenceTier.LOW
    assert _resolve_tier(29) == ConfidenceTier.CRITICAL
