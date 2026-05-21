"""Тесты PDF-aggregator: топ-N контрагентов и налоговая сводка."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from application.services.pdf_data_aggregator import (
    NEW_COUNTERPARTY_THRESHOLD_MONTHS,
    compute_tax_summary,
    compute_top_buyers,
    compute_top_suppliers,
)
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS


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


def _cp(inn: str, name: str, registered: date) -> Counterparty:
    return Counterparty(inn=INN(inn), name=name, registration_date=registered)


def _empty_snapshot(as_of: date = date(2026, 5, 1)) -> BorrowerSnapshot:
    return BorrowerSnapshot(borrower=_borrower(), as_of=as_of)


# ----------------------------- top-N buyers ---------------------------------


def test_top_buyers_sorted_by_share_desc_and_truncated() -> None:
    cps = [
        _cp("200000001", "Buyer A", date(2020, 1, 1)),
        _cp("200000002", "Buyer B", date(2020, 1, 1)),
        _cp("200000003", "Buyer C", date(2020, 1, 1)),
    ]
    shares = {
        "200000001": Decimal("0.10"),
        "200000002": Decimal("0.45"),
        "200000003": Decimal("0.25"),
    }
    snap = BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 1),
        counterparties_buyers=cps,
        buyer_revenue_share=shares,
    )

    result = compute_top_buyers(snap, limit=2)

    assert len(result) == 2
    assert [r.inn for r in result] == ["200000002", "200000003"]
    assert result[0].share_pct == Decimal("45.00")
    assert result[1].share_pct == Decimal("25.00")


def test_top_buyers_skips_inn_without_directory_entry() -> None:
    """Если контрагент в share_map, но нет в counterparties_buyers — пропускаем."""
    cps = [_cp("200000001", "Known", date(2020, 1, 1))]
    shares = {
        "200000001": Decimal("0.30"),
        "999999999": Decimal("0.50"),  # no directory entry
    }
    snap = BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 1),
        counterparties_buyers=cps,
        buyer_revenue_share=shares,
    )

    result = compute_top_buyers(snap)
    assert [r.inn for r in result] == ["200000001"]


def test_top_buyers_marks_recent_registration_as_new() -> None:
    as_of = date(2026, 5, 1)
    cps = [
        _cp("200000001", "Old", date(2020, 1, 1)),
        _cp("200000002", "Fresh", date(2026, 1, 15)),  # ~3.5 мес назад
    ]
    shares = {"200000001": Decimal("0.40"), "200000002": Decimal("0.10")}
    snap = BorrowerSnapshot(
        borrower=_borrower(),
        as_of=as_of,
        counterparties_buyers=cps,
        buyer_revenue_share=shares,
    )

    result = compute_top_buyers(snap)
    by_inn = {r.inn: r for r in result}
    assert by_inn["200000002"].is_new is True
    fresh_months = by_inn["200000002"].months_since_registration
    assert fresh_months is not None
    assert fresh_months < NEW_COUNTERPARTY_THRESHOLD_MONTHS
    assert by_inn["200000001"].is_new is False


def test_top_buyers_empty_when_no_counterparties() -> None:
    assert compute_top_buyers(_empty_snapshot()) == ()


# ----------------------------- top-N suppliers ------------------------------


def test_top_suppliers_uses_supplier_purchase_share() -> None:
    cps = [_cp("300000001", "Supp", date(2019, 1, 1))]
    shares = {"300000001": Decimal("0.60")}
    snap = BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 1),
        counterparties_suppliers=cps,
        supplier_purchase_share=shares,
    )

    result = compute_top_suppliers(snap)
    assert len(result) == 1
    assert result[0].share_pct == Decimal("60.00")


# ----------------------------- tax summary ----------------------------------


def test_tax_summary_collects_delays_within_3y_and_sorts_recent_first() -> None:
    as_of = date(2026, 5, 1)
    events = [
        TaxEvent(date=date(2024, 9, 15), type=TaxEventType.PAYMENT, delay_days=14),
        TaxEvent(date=date(2025, 3, 1), type=TaxEventType.PAYMENT, delay_days=5),
        TaxEvent(date=date(2022, 1, 1), type=TaxEventType.PAYMENT, delay_days=40),  # вне окна
        TaxEvent(date=date(2025, 12, 1), type=TaxEventType.PAYMENT, delay_days=0),  # в срок
    ]
    snap = BorrowerSnapshot(borrower=_borrower(), as_of=as_of, tax_events=events)

    summary = compute_tax_summary(snap)

    assert [d.delay_days for d in summary.delays] == [5, 14]  # сначала более свежие
    assert summary.max_delay_days == 14


def test_tax_summary_aggregates_penalties_within_window() -> None:
    as_of = date(2026, 5, 1)
    events = [
        TaxEvent(
            date=date(2025, 4, 1),
            type=TaxEventType.PENALTY,
            amount=Money(Decimal("1000000"), UZS),
        ),
        TaxEvent(
            date=date(2024, 6, 15),
            type=TaxEventType.PENALTY,
            amount=Money(Decimal("500000"), UZS),
        ),
    ]
    snap = BorrowerSnapshot(borrower=_borrower(), as_of=as_of, tax_events=events)

    summary = compute_tax_summary(snap)
    assert summary.penalties_total == Money(Decimal("1500000"), UZS)


def test_tax_summary_counts_account_freezes_only_within_12_months() -> None:
    as_of = date(2026, 5, 1)
    events = [
        TaxEvent(date=date(2025, 11, 1), type=TaxEventType.ACCOUNT_FREEZE),  # 6 мес назад
        TaxEvent(date=date(2024, 1, 1), type=TaxEventType.ACCOUNT_FREEZE),  # 28 мес назад
    ]
    snap = BorrowerSnapshot(borrower=_borrower(), as_of=as_of, tax_events=events)

    summary = compute_tax_summary(snap)
    assert summary.account_freezes_count_12m == 1
    assert summary.has_freezes_12m is True


def test_tax_summary_empty_state() -> None:
    summary = compute_tax_summary(_empty_snapshot())
    assert summary.delays == ()
    assert summary.max_delay_days == 0
    assert summary.penalties_total is None
    assert summary.account_freezes_count_12m == 0
    assert summary.has_freezes_12m is False
