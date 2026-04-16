"""SINGLE_SUPPLIER_CONCENTRATION: >60% закупок у одного поставщика."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.counterparty.single_supplier_concentration import (
    single_supplier_concentration,
)
from domain.value_objects.inn import INN


def _snapshot(shares: dict[str, Decimal]) -> BorrowerSnapshot:
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
        supplier_purchase_share=shares,
    )


class TestSingleSupplierConcentration:
    def test_fires_when_one_supplier_has_70pct(self) -> None:
        ev = single_supplier_concentration(_snapshot({"111111111": Decimal("0.70")}))
        assert ev is not None

    def test_silent_when_distribution_balanced(self) -> None:
        assert single_supplier_concentration(
            _snapshot({"111111111": Decimal("0.30"), "222222222": Decimal("0.40")})
        ) is None

    def test_silent_at_exactly_60pct(self) -> None:
        assert single_supplier_concentration(_snapshot({"111111111": Decimal("0.60")})) is None

    def test_fires_just_above_60pct(self) -> None:
        assert single_supplier_concentration(_snapshot({"111111111": Decimal("0.61")})) is not None

    def test_silent_with_empty_suppliers(self) -> None:
        assert single_supplier_concentration(_snapshot({})) is None
