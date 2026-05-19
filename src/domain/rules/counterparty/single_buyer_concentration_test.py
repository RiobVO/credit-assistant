"""SINGLE_BUYER_CONCENTRATION: >70% выручки на одном покупателе."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.counterparty.single_buyer_concentration import (
    single_buyer_concentration,
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
            oked_main="62.01",
            registered_address="Ташкент",
        ),
        as_of=date(2026, 5, 8),
        buyer_revenue_share=shares,
    )


class TestSingleBuyerConcentration:
    def test_fires_when_one_buyer_has_80pct(self) -> None:
        ev = single_buyer_concentration(
            _snapshot({"111111111": Decimal("0.80"), "222222222": Decimal("0.20")})
        )
        assert ev is not None
        assert ev.evidence["max_buyer_inn"] == "111111111"

    def test_silent_when_distribution_balanced(self) -> None:
        s = _snapshot(
            {
                "111111111": Decimal("0.30"),
                "222222222": Decimal("0.30"),
                "333333333": Decimal("0.40"),
            }
        )
        assert single_buyer_concentration(s) is None

    def test_silent_at_exactly_70pct(self) -> None:
        # >0.70 строго; 0.70 — silent
        assert single_buyer_concentration(_snapshot({"111111111": Decimal("0.70")})) is None

    def test_fires_just_above_70pct(self) -> None:
        ev = single_buyer_concentration(_snapshot({"111111111": Decimal("0.71")}))
        assert ev is not None

    def test_silent_with_empty_buyers(self) -> None:
        assert single_buyer_concentration(_snapshot({})) is None
