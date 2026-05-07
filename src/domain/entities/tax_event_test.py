"""TaxEvent: налоговое событие — оплата, пеня, заморозка счёта."""

from datetime import date
from decimal import Decimal

from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.value_objects.money import Currency, Money


class TestTaxEventType:
    def test_has_four_types(self) -> None:
        assert {t.value for t in TaxEventType} == {
            "payment",
            "penalty",
            "account_freeze",
            "account_unfreeze",
        }


class TestTaxEventConstruction:
    def test_payment_with_amount(self) -> None:
        ev = TaxEvent(
            date=date(2026, 4, 15),
            type=TaxEventType.PAYMENT,
            amount=Money(Decimal("1000000"), Currency.UZS),
        )
        assert ev.type == TaxEventType.PAYMENT
        assert ev.amount is not None

    def test_freeze_carries_duration(self) -> None:
        ev = TaxEvent(
            date=date(2026, 1, 10),
            type=TaxEventType.ACCOUNT_FREEZE,
            duration_days=14,
        )
        assert ev.duration_days == 14

    def test_payment_with_delay_days(self) -> None:
        # Для TAX_PAYMENT_DELAYS правила
        ev = TaxEvent(
            date=date(2026, 4, 30),
            type=TaxEventType.PAYMENT,
            amount=Money(100, Currency.UZS),
            delay_days=45,
        )
        assert ev.delay_days == 45
