"""Unit-тесты для scripts.seed_demo_borrowers — 5 deterministic demo dossiers."""
from __future__ import annotations

from datetime import date, timedelta

from scripts.seed_demo_borrowers import (
    DEMO_AS_OF,
    DEMO_BORROWERS,
    KADR_DON_NON,
    _build_borrower,
    _build_chunk,
    _build_dossier_specs,
    build_demo_borrowers,
)

from domain.entities.borrower import LegalForm
from domain.value_objects.money import Currency


def test_returns_five_deterministic_dossier_specs() -> None:
    specs = _build_dossier_specs()
    assert len(specs) == 5
    case_ids = {d.case_id for _, d in specs}
    assert case_ids == {
        "BR-2026-0030",
        "BR-2026-0040",
        "BR-2026-0042",
        "BR-2026-0046",
        "BR-2026-0047",
    }


def test_legacy_demo_borrowers_returns_five_specs() -> None:
    """Старый API (DEMO_BORROWERS) обновлён под 5 dossiers."""
    assert len(build_demo_borrowers()) == 5
    assert len(DEMO_BORROWERS) == 5


def test_three_dossiers_share_same_ip_inn() -> None:
    """BR-0030/0046/0047 — narrative «один заёмщик три снимка»."""
    specs = _build_dossier_specs()
    ip_dossiers = [
        d for b, d in specs if b.inn == KADR_DON_NON.inn
    ]
    assert len(ip_dossiers) == 3
    assert {d.case_id for d in ip_dossiers} == {
        "BR-2026-0030",
        "BR-2026-0046",
        "BR-2026-0047",
    }


def test_clean_scenarios_have_no_loan_no_vat() -> None:
    """BR-0040 / BR-0042 — clean approve: ни заёма, ни VAT-mismatch."""
    specs = _build_dossier_specs()
    by_case = {d.case_id: d for _, d in specs}
    for case_id in ("BR-2026-0040", "BR-2026-0042"):
        d = by_case[case_id]
        assert d.loan_request is None
        assert d.vat_period is None
        assert len(d.annual) == 2  # prior + current year, чистый snapshot


def test_br0046_has_vat_mismatch_and_recent_director() -> None:
    """BR-0046 fires VAT_ESF_MISMATCH (23%) + DIRECTOR_CHANGED_6M (65 days)."""
    specs = _build_dossier_specs()
    _, d = next((b, dd) for b, dd in specs if dd.case_id == "BR-2026-0046")
    assert d.vat_period is not None
    year, month, declared, esf = d.vat_period
    diff = abs(declared - esf) / declared
    assert diff > 0.15, "должно быть >15% для VAT_ESF_MISMATCH"
    assert d.director_appointed_at_override is not None
    days = (d.as_of - d.director_appointed_at_override).days
    assert 0 < days <= 180, "директор сменился в окне 180 дней"


def test_br0047_insufficient_data_and_huge_loan() -> None:
    """BR-0047 — no revenue at all + huge loan → INSUFFICIENT_DATA + LOAN_TO_REVENUE."""
    specs = _build_dossier_specs()
    _, d = next((b, dd) for b, dd in specs if dd.case_id == "BR-2026-0047")
    assert d.annual == ()
    assert d.quarterly_revenue == ()
    assert d.loan_request is not None
    assert d.loan_request.amount.amount > 500_000_000_000  # 555.5 млрд


def test_build_borrower_uses_director_override() -> None:
    """director_appointed_at_override побеждает базовое значение."""
    specs = _build_dossier_specs()
    b_spec, d_spec = next(
        (b, d) for b, d in specs if d.case_id == "BR-2026-0030"
    )
    borrower = _build_borrower(b_spec, d_spec)
    assert d_spec.director_appointed_at_override is not None
    assert borrower.director_appointed_at == d_spec.director_appointed_at_override
    assert borrower.legal_form is LegalForm.IE


def test_build_chunk_emits_vat_period_for_br0046() -> None:
    specs = _build_dossier_specs()
    b_spec, d_spec = next(
        (b, d) for b, d in specs if d.case_id == "BR-2026-0046"
    )
    chunk = _build_chunk(b_spec, d_spec)
    assert len(chunk.vat_periods) == 1
    vp = chunk.vat_periods[0]
    assert vp.vat_declared is not None
    assert vp.vat_declared.currency is Currency.UZS
    assert vp.period.start == date(2026, 3, 1)
    assert vp.period.end == date(2026, 3, 31)


def test_build_chunk_emits_loan_request() -> None:
    specs = _build_dossier_specs()
    b_spec, d_spec = next(
        (b, d) for b, d in specs if d.case_id == "BR-2026-0046"
    )
    chunk = _build_chunk(b_spec, d_spec)
    assert chunk.loan_request is not None
    assert chunk.loan_request.amount.amount > 500_000_000


def test_demo_as_of_anchored_to_2026() -> None:
    assert DEMO_AS_OF.year == 2026
    # Дольше чем 6 месяцев от base director_appointed_at для ZUMRAD — clean.
    assert (DEMO_AS_OF - date(2021, 2, 15)).days > 365
