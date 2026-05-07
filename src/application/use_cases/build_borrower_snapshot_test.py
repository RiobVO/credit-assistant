"""Тесты use case build_borrower_snapshot — слияние chunks в snapshot."""

from datetime import date
from decimal import Decimal

import pytest

from application.dto.parsed_data_chunk import EsfChunk, ManualChunk, SoliqChunk
from application.use_cases.build_borrower_snapshot import (
    ChunkBorrowerMismatchError,
    build_borrower_snapshot,
)
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.counterparty import Counterparty
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice, InvoiceRole
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS
BORROWER_INN = INN("306399449")
AS_OF = date(2026, 5, 8)


def _borrower() -> Borrower:
    return Borrower(
        inn=BORROWER_INN,
        name="ООО AZ RUHDIL SAVDO",
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 5, 1),
        director_name="Иванов",
        director_appointed_at=date(2020, 1, 1),
        okved_main="46.49",
        registered_address="Ташкент",
    )


def _invoice(
    when: date = date(2025, 6, 1),
    role: InvoiceRole = InvoiceRole.SELLER,
    cp_inn: str = "303069092",
    amount: int = 1_000_000,
) -> Invoice:
    return Invoice(
        date=when,
        amount=Money(Decimal(amount), UZS),
        our_role=role,
        counterparty_inn=INN(cp_inn),
        counterparty_name="Контрагент",
    )


def _annual(year: int, revenue: int) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=Money(Decimal(revenue), UZS),
        net_profit=Money(0, UZS),
        taxes_paid=Money(0, UZS),
    )


class TestBorrowerAndAsOf:
    def test_passes_borrower_and_as_of_through(self) -> None:
        snap = build_borrower_snapshot(borrower=_borrower(), as_of=AS_OF, chunks=[])
        assert snap.borrower.inn == BORROWER_INN
        assert snap.as_of == AS_OF

    def test_empty_chunks_produce_empty_snapshot(self) -> None:
        snap = build_borrower_snapshot(borrower=_borrower(), as_of=AS_OF, chunks=[])
        assert snap.invoices == []
        assert snap.annual_reports == []
        assert snap.tax_events == []
        assert snap.esf_seller_vat_total is None
        assert snap.loan_request_amount is None


class TestEsfChunk:
    def test_esf_chunk_populates_invoices(self) -> None:
        chunk = EsfChunk(
            borrower_inn=BORROWER_INN,
            invoices=[_invoice(amount=1), _invoice(amount=2)],
        )
        snap = build_borrower_snapshot(
            borrower=_borrower(), as_of=AS_OF, chunks=[chunk],
        )
        assert len(snap.invoices) == 2
        assert {i.amount.amount for i in snap.invoices} == {Decimal(1), Decimal(2)}

    def test_esf_chunk_does_not_touch_financial_reports(self) -> None:
        chunk = EsfChunk(borrower_inn=BORROWER_INN, invoices=[_invoice()])
        snap = build_borrower_snapshot(
            borrower=_borrower(), as_of=AS_OF, chunks=[chunk],
        )
        assert snap.annual_reports == []
        assert snap.esf_seller_vat_total is None


class TestSoliqChunk:
    def test_populates_financial_reports_tax_events_and_vat(self) -> None:
        chunk = SoliqChunk(
            borrower_inn=BORROWER_INN,
            annual_reports=[_annual(2025, 5_000_000_000)],
            quarterly_reports=[
                FinancialReport(
                    period=DateRange(date(2025, 1, 1), date(2025, 3, 31)),
                    revenue=Money(Decimal(1_000_000_000), UZS),
                    net_profit=Money(0, UZS),
                    taxes_paid=Money(0, UZS),
                ),
            ],
            monthly_turnover=[
                MonthlyTurnover(month_start=date(2025, 1, 1), revenue=Money(100, UZS)),
            ],
            tax_events=[
                TaxEvent(date=date(2025, 7, 1), type=TaxEventType.PAYMENT,
                         amount=Money(Decimal(50_000), UZS)),
            ],
            esf_seller_vat_total=Money(Decimal(60_000_000), UZS),
        )
        snap = build_borrower_snapshot(
            borrower=_borrower(), as_of=AS_OF, chunks=[chunk],
        )
        assert len(snap.annual_reports) == 1
        assert len(snap.quarterly_reports) == 1
        assert len(snap.monthly_turnover) == 1
        assert len(snap.tax_events) == 1
        assert snap.esf_seller_vat_total is not None
        assert snap.esf_seller_vat_total.amount == Decimal(60_000_000)

    def test_vat_aggregate_remains_none_when_chunk_omits_it(self) -> None:
        chunk = SoliqChunk(borrower_inn=BORROWER_INN)
        snap = build_borrower_snapshot(
            borrower=_borrower(), as_of=AS_OF, chunks=[chunk],
        )
        assert snap.esf_seller_vat_total is None


class TestManualChunk:
    def test_populates_counterparties_and_shares(self) -> None:
        buyer = Counterparty(
            inn=INN("303069092"), name="ООО Покупатель",
            registration_date=date(2018, 1, 1),
        )
        chunk = ManualChunk(
            borrower_inn=BORROWER_INN,
            counterparties_buyers=[buyer],
            buyer_revenue_share={"303069092": Decimal("0.45")},
            supplier_purchase_share={"500000001": Decimal("0.30")},
        )
        snap = build_borrower_snapshot(
            borrower=_borrower(), as_of=AS_OF, chunks=[chunk],
        )
        assert snap.counterparties_buyers == [buyer]
        assert snap.buyer_revenue_share["303069092"] == Decimal("0.45")
        assert snap.supplier_purchase_share["500000001"] == Decimal("0.30")

    def test_loan_amount_picked_up_from_manual_chunk(self) -> None:
        chunk = ManualChunk(
            borrower_inn=BORROWER_INN,
            loan_request_amount=Money(Decimal(100_000_000), UZS),
        )
        snap = build_borrower_snapshot(
            borrower=_borrower(), as_of=AS_OF, chunks=[chunk],
        )
        assert snap.loan_request_amount is not None
        assert snap.loan_request_amount.amount == Decimal(100_000_000)


class TestLoanAmountPriority:
    def test_explicit_param_wins_over_manual_chunk(self) -> None:
        chunk = ManualChunk(
            borrower_inn=BORROWER_INN,
            loan_request_amount=Money(Decimal(50_000_000), UZS),
        )
        snap = build_borrower_snapshot(
            borrower=_borrower(),
            as_of=AS_OF,
            chunks=[chunk],
            loan_request_amount=Money(Decimal(200_000_000), UZS),
        )
        assert snap.loan_request_amount is not None
        assert snap.loan_request_amount.amount == Decimal(200_000_000)


class TestMerge:
    def test_multiple_chunks_merge_invoices_and_financials(self) -> None:
        esf = EsfChunk(
            borrower_inn=BORROWER_INN,
            invoices=[_invoice(when=date(2025, 1, 5), amount=100)],
        )
        manual = ManualChunk(
            borrower_inn=BORROWER_INN,
            invoices=[_invoice(when=date(2025, 2, 5), amount=200)],
            annual_reports=[_annual(2024, 1)],
        )
        soliq = SoliqChunk(
            borrower_inn=BORROWER_INN,
            annual_reports=[_annual(2025, 2)],
        )
        snap = build_borrower_snapshot(
            borrower=_borrower(), as_of=AS_OF, chunks=[esf, manual, soliq],
        )
        assert len(snap.invoices) == 2
        assert len(snap.annual_reports) == 2  # дубликаты не resolve, см. ADR (TODO)


class TestBorrowerMismatch:
    def test_esf_chunk_with_wrong_inn_raises(self) -> None:
        chunk = EsfChunk(borrower_inn=INN("999999999"), invoices=[])
        with pytest.raises(ChunkBorrowerMismatchError) as exc:
            build_borrower_snapshot(
                borrower=_borrower(), as_of=AS_OF, chunks=[chunk],
            )
        assert exc.value.chunk_type == "EsfChunk"
        assert exc.value.expected.value == BORROWER_INN.value
        assert exc.value.actual.value == "999999999"

    def test_soliq_chunk_with_wrong_inn_raises(self) -> None:
        chunk = SoliqChunk(borrower_inn=INN("999999999"))
        with pytest.raises(ChunkBorrowerMismatchError):
            build_borrower_snapshot(
                borrower=_borrower(), as_of=AS_OF, chunks=[chunk],
            )

    def test_manual_chunk_with_wrong_inn_raises(self) -> None:
        chunk = ManualChunk(borrower_inn=INN("999999999"))
        with pytest.raises(ChunkBorrowerMismatchError):
            build_borrower_snapshot(
                borrower=_borrower(), as_of=AS_OF, chunks=[chunk],
            )
