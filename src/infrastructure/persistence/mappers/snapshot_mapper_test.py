"""Snapshot mapper: round-trip + JSON-сериализуемость payload."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice, InvoiceRole
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money
from infrastructure.persistence.mappers.snapshot_mapper import (
    snapshot_from_payload,
    snapshot_to_payload,
)

UZS = Currency.UZS


def _money(amount: str | int) -> Money:
    return Money(Decimal(amount), UZS)


def _borrower() -> Borrower:
    return Borrower(
        inn=INN("123456789"),
        name='ООО "Тест"',
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 1, 1),
        director_name="Иванов",
        director_appointed_at=date(2022, 1, 1),
        okved_main="62.01",
        registered_address="Ташкент",
    )


def _full_snapshot() -> BorrowerSnapshot:
    """Snapshot со всеми полями заполненными."""
    return BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 8),
        annual_reports=[
            FinancialReport(
                period=DateRange(start=date(2024, 1, 1), end=date(2024, 12, 31)),
                revenue=_money(5_000_000_000),
                net_profit=_money(500_000_000),
                taxes_paid=_money(120_000_000),
                vat_declared=_money(300_000_000),
                assets=_money(4_000_000_000),
                liabilities=_money(2_000_000_000),
            ),
        ],
        quarterly_reports=[
            FinancialReport(
                period=DateRange(start=date(2025, 1, 1), end=date(2025, 3, 31)),
                revenue=_money(1_200_000_000),
                net_profit=_money(80_000_000),
                taxes_paid=_money(20_000_000),
            ),
        ],
        monthly_turnover=[
            MonthlyTurnover(
                month_start=date(2026, 3, 1),
                revenue=_money(400_000_000),
                vat_obligations=_money(48_000_000),
            ),
            MonthlyTurnover(month_start=date(2026, 4, 1), revenue=_money(380_000_000)),
        ],
        counterparties_buyers=[
            Counterparty(
                inn=INN("200000020"),
                name="Покупатель",
                registration_date=date(2024, 1, 1),
            ),
        ],
        counterparties_suppliers=[
            Counterparty(
                inn=INN("300000030"),
                name="Поставщик",
                registration_date=date(2019, 1, 1),
            ),
        ],
        buyer_revenue_share={"200000020": Decimal("0.5")},
        supplier_purchase_share={"300000030": Decimal("0.7")},
        invoices=[
            Invoice(
                date=date(2025, 6, 1),
                amount=_money(500_000_000),
                our_role=InvoiceRole.SELLER,
                counterparty_inn=INN("200000020"),
                counterparty_name="Покупатель",
            ),
        ],
        tax_events=[
            TaxEvent(date=date(2026, 3, 1), type=TaxEventType.PAYMENT, delay_days=45),
            TaxEvent(
                date=date(2026, 2, 1),
                type=TaxEventType.PENALTY,
                amount=_money(50_000_000),
            ),
            TaxEvent(
                date=date(2025, 11, 1),
                type=TaxEventType.ACCOUNT_FREEZE,
                duration_days=30,
            ),
        ],
        esf_seller_vat_total=_money(60_000_000),
        loan_request_amount=_money(1_500_000_000),
    )


def test_snapshot_round_trip_full() -> None:
    original = _full_snapshot()
    payload = snapshot_to_payload(original)
    restored = snapshot_from_payload(payload, original.borrower)
    assert restored == original


def test_snapshot_round_trip_empty() -> None:
    # Все коллекции пустые, опциональные поля None.
    original = BorrowerSnapshot(borrower=_borrower(), as_of=date(2026, 5, 8))
    payload = snapshot_to_payload(original)
    restored = snapshot_from_payload(payload, original.borrower)
    assert restored == original


def test_snapshot_payload_is_json_serializable() -> None:
    # JSONB на стороне Postgres делает json.dumps внутри драйвера —
    # payload не должен содержать Decimal/date/INN/Money объектов.
    payload = snapshot_to_payload(_full_snapshot())
    serialized = json.dumps(payload, ensure_ascii=False)
    # Sanity: round-trip через json не теряет структуру.
    assert json.loads(serialized) == payload


def test_snapshot_decimal_precision_preserved() -> None:
    original = BorrowerSnapshot(
        borrower=_borrower(),
        as_of=date(2026, 5, 8),
        buyer_revenue_share={
            "200000020": Decimal("0.123456789012345"),  # высокая точность
        },
    )
    payload = snapshot_to_payload(original)
    restored = snapshot_from_payload(payload, original.borrower)
    assert restored.buyer_revenue_share == original.buyer_revenue_share
