"""Smoke + domain-factory tests for demo seed script."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from scripts.seed_demo_borrowers import (
    DEMO_BORROWERS,
    DEMO_CURRENT_YEAR,
    _spec_to_borrower,
    _spec_to_chunk,
    build_demo_borrowers,
)

from domain.entities.borrower import LegalForm
from domain.value_objects.money import Currency


def test_returns_three_demo_borrowers() -> None:
    borrowers = build_demo_borrowers()
    assert len(borrowers) == 3
    inns = {b["inn"] for b in borrowers}
    assert len(inns) == 3, "ИНН должны быть уникальными"


def test_each_has_realistic_quarterly_revenue() -> None:
    borrowers = build_demo_borrowers()
    for b in borrowers:
        revenue = b["quarterly_revenue"]
        assert len(revenue) == 8, "8 кварталов (2 года)"
        values = [float(v) for v in revenue]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance**0.5
        cv = std / mean if mean > 0 else 0
        assert cv >= 0.05, f"Слишком ровная выручка (cv={cv:.3f}) — добавь сезонность"


def test_retail_has_q4_peak() -> None:
    borrowers = build_demo_borrowers()
    retail = next(b for b in borrowers if b["industry"] == "retail")
    q1, q2, q3, q4, q5, q6, q7, q8 = retail["quarterly_revenue"]
    assert q4 > q1 and q4 > q2 and q4 > q3
    assert q8 > q5 and q8 > q6 and q8 > q7


def test_agro_has_q2_q3_peak() -> None:
    borrowers = build_demo_borrowers()
    agro = next(b for b in borrowers if b["industry"] == "agro")
    quarterly = agro["quarterly_revenue"]
    q1, q2, q3, q4 = quarterly[:4]
    peak = max(q2, q3)
    assert peak > q1 and peak > q4


# ──────────────── domain factory tests ────────────────


def test_spec_to_borrower_maps_farm_to_other_legal_form() -> None:
    agro_spec = next(s for s in DEMO_BORROWERS if s["legal_form"] == "FARM")
    borrower = _spec_to_borrower(agro_spec)
    assert borrower.legal_form is LegalForm.OTHER
    assert borrower.inn.value == agro_spec["inn"]


def test_spec_to_borrower_preserves_dates_and_okved() -> None:
    retail_spec = next(s for s in DEMO_BORROWERS if s["industry"] == "retail")
    borrower = _spec_to_borrower(retail_spec)
    assert borrower.registration_date == date(2017, 4, 12)
    assert borrower.director_appointed_at == date(2021, 2, 15)
    assert borrower.oked_main == "47.51"


def test_spec_to_chunk_emits_two_annuals_aligned_to_demo_year() -> None:
    retail_spec = next(s for s in DEMO_BORROWERS if s["industry"] == "retail")
    chunk = _spec_to_chunk(retail_spec)
    assert len(chunk.annual_reports) == 2
    years = {r.period.start.year for r in chunk.annual_reports}
    assert years == {DEMO_CURRENT_YEAR - 1, DEMO_CURRENT_YEAR}
    for report in chunk.annual_reports:
        assert report.period.start.month == 1
        assert report.period.end.month == 12
        assert report.revenue.currency is Currency.UZS
        assert report.taxes_paid is not None
        # net_profit_pct=0.06 ⇒ net_profit ≈ 6% от annual revenue.
        margin = report.net_profit.amount / report.revenue.amount
        assert abs(margin - Decimal("0.06")) < Decimal("0.001")


def test_spec_to_chunk_emits_24_monthly_with_first_day() -> None:
    services_spec = next(s for s in DEMO_BORROWERS if s["industry"] == "services")
    chunk = _spec_to_chunk(services_spec)
    assert len(chunk.monthly_turnover) == 24
    for mt in chunk.monthly_turnover:
        assert mt.month_start.day == 1
        assert mt.revenue.currency is Currency.UZS
    # Покрытие 24 различных месяцев — нет дублей.
    months = {mt.month_start for mt in chunk.monthly_turnover}
    assert len(months) == 24


def test_spec_to_chunk_quarterly_revenue_distributes_evenly_over_3_months() -> None:
    """Квартальная выручка делится на 3 равных месяца — детерминированно."""
    retail_spec = next(s for s in DEMO_BORROWERS if s["industry"] == "retail")
    chunk = _spec_to_chunk(retail_spec)
    # Q1 prior year (2024): seasonality[0] = 0.9, base = 3.2e9 / 4 = 8e8.
    # Q1 amount = 0.9 * 8e8 = 7.2e8. Per month = 2.4e8.
    q1_months = [mt for mt in chunk.monthly_turnover if mt.month_start.year == 2024
                 and mt.month_start.month in (1, 2, 3)]
    assert len(q1_months) == 3
    amounts = {mt.revenue.amount for mt in q1_months}
    # Все три месяца — одна сумма.
    assert len(amounts) == 1
