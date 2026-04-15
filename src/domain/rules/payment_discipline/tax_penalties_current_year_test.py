"""TAX_PENALTIES_CURRENT_YEAR: пеня по налогам в текущем календарном году."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.rules.payment_discipline.tax_penalties_current_year import (
    tax_penalties_current_year,
)
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS
AS_OF = date(2026, 5, 8)


def _snapshot(*events: TaxEvent) -> BorrowerSnapshot:
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
        as_of=AS_OF,
        tax_events=list(events),
    )


def _penalty(when: date, amount: int) -> TaxEvent:
    return TaxEvent(date=when, type=TaxEventType.PENALTY, amount=Money(Decimal(amount), UZS))


class TestTaxPenaltiesCurrentYear:
    def test_fires_when_penalty_in_current_year(self) -> None:
        ev = tax_penalties_current_year(_snapshot(_penalty(date(2026, 3, 1), 50_000_000)))
        assert ev is not None
        assert ev.evidence["count"] == 1

    def test_silent_when_penalty_only_in_previous_year(self) -> None:
        prev = _penalty(date(2025, 12, 31), 50_000_000)
        assert tax_penalties_current_year(_snapshot(prev)) is None

    def test_silent_with_no_events(self) -> None:
        assert tax_penalties_current_year(_snapshot()) is None

    def test_silent_when_only_payment_events(self) -> None:
        payment = TaxEvent(date=date(2026, 3, 1), type=TaxEventType.PAYMENT)
        assert tax_penalties_current_year(_snapshot(payment)) is None

    def test_aggregates_multiple_penalties(self) -> None:
        ev = tax_penalties_current_year(
            _snapshot(
                _penalty(date(2026, 1, 15), 10_000_000),
                _penalty(date(2026, 4, 30), 25_000_000),
            )
        )
        assert ev is not None
        assert ev.evidence["count"] == 2
        assert ev.evidence["total_amount"] == "35000000"
