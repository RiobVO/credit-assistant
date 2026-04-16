"""Invoice (ЭСФ): счёт-фактура с указанием направления (продавец/покупатель)."""

from datetime import date
from decimal import Decimal

from domain.entities.invoice import Invoice, InvoiceRole
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money


def _inv() -> Invoice:
    return Invoice(
        date=date(2026, 4, 15),
        amount=Money(Decimal("1000000"), Currency.UZS),
        vat_amount=Money(Decimal("120000"), Currency.UZS),
        our_role=InvoiceRole.SELLER,
        counterparty_inn=INN("987654321"),
        counterparty_name="ООО Покупатель",
    )


class TestInvoiceRole:
    def test_has_two_directions(self) -> None:
        assert {r.value for r in InvoiceRole} == {"seller", "buyer"}


class TestInvoiceConstruction:
    def test_creates_with_all_fields(self) -> None:
        inv = _inv()
        assert inv.our_role == InvoiceRole.SELLER
        assert inv.counterparty_inn.value == "987654321"

    def test_amount_and_vat_in_same_currency(self) -> None:
        inv = _inv()
        assert inv.amount.currency == inv.vat_amount.currency
