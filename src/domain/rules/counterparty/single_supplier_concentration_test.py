"""SINGLE_SUPPLIER_CONCENTRATION: dual-severity foreign/domestic концентрации."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.rules.counterparty.single_supplier_concentration import (
    single_supplier_concentration,
)
from domain.value_objects.flag_severity import FlagSeverity
from domain.value_objects.inn import INN


def _supplier(inn: str, *, is_foreign: bool = False) -> Counterparty:
    return Counterparty(
        inn=INN(inn),
        name=f"Поставщик {inn}",
        registration_date=date(2020, 1, 1),
        is_foreign=is_foreign,
    )


def _snapshot(
    shares: dict[str, Decimal],
    suppliers: list[Counterparty] | None = None,
) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=Borrower(
            inn=INN("123456789"),
            name="ООО",
            legal_form=LegalForm.LLC,
            registration_date=date(2020, 1, 1),
            director_name="Иванов",
            director_appointed_at=date(2020, 1, 1),
            oked_main="62.01",
            registered_address="Ташкент",
        ),
        as_of=date(2026, 5, 8),
        supplier_purchase_share=shares,
        counterparties_suppliers=suppliers or [],
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


class TestSingleSupplierForeignEscalation:
    """ADR-0024 Session 3: foreign supplier эскалирует severity до HIGH."""

    def test_foreign_supplier_at_55pct_fires_high(self) -> None:
        # Foreign > 0.50 → severity=HIGH.
        ev = single_supplier_concentration(
            _snapshot(
                {"111111111": Decimal("0.55")},
                suppliers=[_supplier("111111111", is_foreign=True)],
            )
        )
        assert ev is not None
        assert ev.severity == FlagSeverity.HIGH
        assert ev.evidence["max_supplier_is_foreign"] is True

    def test_domestic_supplier_at_55pct_silent(self) -> None:
        # Domestic 0.55 < 0.60 → silent (старая логика).
        ev = single_supplier_concentration(
            _snapshot(
                {"111111111": Decimal("0.55")},
                suppliers=[_supplier("111111111", is_foreign=False)],
            )
        )
        assert ev is None

    def test_domestic_supplier_at_65pct_fires_medium(self) -> None:
        # Domestic > 0.60 → fires без override (medium из YAML).
        ev = single_supplier_concentration(
            _snapshot(
                {"111111111": Decimal("0.65")},
                suppliers=[_supplier("111111111", is_foreign=False)],
            )
        )
        assert ev is not None
        assert ev.severity is None  # fallback на rule.severity = medium
        assert ev.evidence["max_supplier_is_foreign"] is False

    def test_foreign_supplier_at_65pct_fires_high(self) -> None:
        # Foreign > 0.50 берёт верх над domestic 0.60 — severity=HIGH.
        ev = single_supplier_concentration(
            _snapshot(
                {"111111111": Decimal("0.65")},
                suppliers=[_supplier("111111111", is_foreign=True)],
            )
        )
        assert ev is not None
        assert ev.severity == FlagSeverity.HIGH

    def test_missing_counterparty_lookup_falls_back_to_domestic(self) -> None:
        # supplier_purchase_share без соответствующего Counterparty в
        # counterparties_suppliers — is_foreign=False (conservative).
        ev = single_supplier_concentration(
            _snapshot({"111111111": Decimal("0.65")}, suppliers=[])
        )
        assert ev is not None
        assert ev.severity is None  # medium из YAML
        assert ev.evidence["max_supplier_is_foreign"] is False
