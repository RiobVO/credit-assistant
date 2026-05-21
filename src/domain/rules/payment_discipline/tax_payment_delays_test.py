"""TAX_PAYMENT_DELAYS: задержки уплаты налогов >30 дней."""

from datetime import date

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.rules.payment_discipline.tax_payment_delays import tax_payment_delays
from domain.value_objects.inn import INN


def _snapshot(*events: TaxEvent) -> BorrowerSnapshot:
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
        tax_events=list(events),
    )


def _payment(delay_days: int | None) -> TaxEvent:
    return TaxEvent(
        date=date(2026, 4, 15),
        type=TaxEventType.PAYMENT,
        delay_days=delay_days,
    )


class TestTaxPaymentDelays:
    def test_fires_when_45_day_delay(self) -> None:
        ev = tax_payment_delays(_snapshot(_payment(45)))
        assert ev is not None
        assert ev.evidence["max_delay_days"] == 45

    def test_silent_at_10_day_delay(self) -> None:
        assert tax_payment_delays(_snapshot(_payment(10))) is None

    def test_silent_at_exactly_30_days(self) -> None:
        # >30 строго, ровно 30 — silent
        assert tax_payment_delays(_snapshot(_payment(30))) is None

    def test_fires_at_31_days(self) -> None:
        assert tax_payment_delays(_snapshot(_payment(31))) is not None

    def test_silent_with_no_tax_events(self) -> None:
        assert tax_payment_delays(_snapshot()) is None

    def test_silent_when_only_non_payment_events(self) -> None:
        penalty = TaxEvent(date=date(2026, 1, 1), type=TaxEventType.PENALTY)
        assert tax_payment_delays(_snapshot(penalty)) is None

    def test_counts_multiple_delayed_payments(self) -> None:
        ev = tax_payment_delays(_snapshot(_payment(45), _payment(60), _payment(20)))
        assert ev is not None
        assert ev.evidence["delayed_count"] == 2  # 45 и 60, не 20
        assert ev.evidence["max_delay_days"] == 60
