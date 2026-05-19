"""CIRCULAR_INVOICING (упрощ.): 2-узловые циклы A→B + B→A в близком окне."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.invoice import Invoice, InvoiceRole
from domain.rules.counterparty.circular_invoicing import circular_invoicing
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS
# ADR-0024: MIN_PAIR_VOLUME = 100_000_000 UZS. Default amount = 60 млн UZS
# на одну фактуру → пара 60+60 = 120M > порог. Для negative-cases используется
# 30 млн (пара 60M < порог).
DEFAULT_INVOICE_AMOUNT = 60_000_000


def _inv(
    when: date,
    role: InvoiceRole,
    cp_inn: str = "987654321",
    amount: int = DEFAULT_INVOICE_AMOUNT,
) -> Invoice:
    return Invoice(
        date=when,
        amount=Money(Decimal(amount), UZS),
        our_role=role,
        counterparty_inn=INN(cp_inn),
        counterparty_name="ООО",
    )


def _snapshot(*invoices: Invoice) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=Borrower(
            inn=INN("123456789"),
            name="ООО",
            legal_form=LegalForm.LLC,
            registration_date=date(2020, 1, 1),
            director_name="Иванов",
            director_appointed_at=date(2020, 1, 1),
            okved_main="62.01",
            registered_address="Ташкент",
        ),
        as_of=date(2026, 5, 8),
        invoices=list(invoices),
    )


class TestCircularInvoicing:
    def test_fires_for_seller_buyer_pair_within_window(self) -> None:
        ev = circular_invoicing(_snapshot(
            _inv(date(2026, 4, 1), InvoiceRole.SELLER),
            _inv(date(2026, 4, 15), InvoiceRole.BUYER),
        ))
        assert ev is not None
        assert ev.evidence["cycle_count"] == 1

    def test_silent_for_only_one_direction(self) -> None:
        assert circular_invoicing(_snapshot(
            _inv(date(2026, 4, 1), InvoiceRole.SELLER),
            _inv(date(2026, 4, 15), InvoiceRole.SELLER),
        )) is None

    def test_silent_when_pair_too_far_apart(self) -> None:
        # >90 дней между sell и buy → не цикл
        assert circular_invoicing(_snapshot(
            _inv(date(2026, 1, 1), InvoiceRole.SELLER),
            _inv(date(2026, 5, 1), InvoiceRole.BUYER),
        )) is None

    def test_silent_for_different_counterparties(self) -> None:
        # Sell к одному, buy от другого — не цикл
        assert circular_invoicing(_snapshot(
            _inv(date(2026, 4, 1), InvoiceRole.SELLER, cp_inn="987654321"),
            _inv(date(2026, 4, 15), InvoiceRole.BUYER, cp_inn="555555555"),
        )) is None

    def test_silent_with_no_invoices(self) -> None:
        assert circular_invoicing(_snapshot()) is None

    def test_silent_when_pair_below_material_threshold(self) -> None:
        # ADR-0024: пара 30M+30M = 60M < 100M порог → silent (рутинное)
        assert circular_invoicing(_snapshot(
            _inv(date(2026, 4, 1), InvoiceRole.SELLER, amount=30_000_000),
            _inv(date(2026, 4, 15), InvoiceRole.BUYER, amount=30_000_000),
        )) is None

    def test_counts_multiple_distinct_cycles(self) -> None:
        ev = circular_invoicing(_snapshot(
            _inv(date(2026, 4, 1), InvoiceRole.SELLER, cp_inn="111111111"),
            _inv(date(2026, 4, 15), InvoiceRole.BUYER, cp_inn="111111111"),
            _inv(date(2026, 3, 1), InvoiceRole.SELLER, cp_inn="222222222"),
            _inv(date(2026, 3, 20), InvoiceRole.BUYER, cp_inn="222222222"),
        ))
        assert ev is not None
        assert ev.evidence["cycle_count"] == 2
