"""Smoke test for demo seed script."""
from __future__ import annotations

from scripts.seed_demo_borrowers import build_demo_borrowers


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
    quarterly = retail["quarterly_revenue"]
    q1, q2, q3, q4, q5, q6, q7, q8 = quarterly
    assert q4 > q1 and q4 > q2 and q4 > q3
    assert q8 > q5 and q8 > q6 and q8 > q7


def test_agro_has_q2_q3_peak() -> None:
    borrowers = build_demo_borrowers()
    agro = next(b for b in borrowers if b["industry"] == "agro")
    quarterly = agro["quarterly_revenue"]
    q1, q2, q3, q4, q5, q6, q7, q8 = quarterly
    peak = max(q2, q3)
    assert peak > q1 and peak > q4
