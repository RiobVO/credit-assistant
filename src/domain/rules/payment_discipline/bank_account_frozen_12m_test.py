"""BANK_ACCOUNT_FROZEN_12M: приостановка счёта Soliq за последние 12 мес."""

from datetime import date, timedelta

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.rules.payment_discipline.bank_account_frozen_12m import (
    bank_account_frozen_12m,
)
from domain.value_objects.inn import INN

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


def _freeze(when: date) -> TaxEvent:
    return TaxEvent(date=when, type=TaxEventType.ACCOUNT_FREEZE, duration_days=14)


class TestBankAccountFrozen12m:
    def test_fires_when_freeze_6_months_ago(self) -> None:
        ev = bank_account_frozen_12m(_snapshot(_freeze(AS_OF - timedelta(days=180))))
        assert ev is not None

    def test_silent_when_freeze_18_months_ago(self) -> None:
        assert bank_account_frozen_12m(_snapshot(_freeze(AS_OF - timedelta(days=540)))) is None

    def test_fires_at_boundary_365_days(self) -> None:
        # Включительно: ровно 365 дней назад — ещё в окне
        ev = bank_account_frozen_12m(_snapshot(_freeze(AS_OF - timedelta(days=365))))
        assert ev is not None

    def test_silent_at_366_days(self) -> None:
        assert bank_account_frozen_12m(_snapshot(_freeze(AS_OF - timedelta(days=366)))) is None

    def test_silent_with_no_events(self) -> None:
        assert bank_account_frozen_12m(_snapshot()) is None

    def test_silent_when_only_unfreeze_events(self) -> None:
        unfreeze = TaxEvent(date=AS_OF - timedelta(days=30), type=TaxEventType.ACCOUNT_UNFREEZE)
        assert bank_account_frozen_12m(_snapshot(unfreeze)) is None

    def test_counts_multiple_freezes(self) -> None:
        ev = bank_account_frozen_12m(
            _snapshot(
                _freeze(AS_OF - timedelta(days=30)),
                _freeze(AS_OF - timedelta(days=200)),
            )
        )
        assert ev is not None
        assert ev.evidence["freeze_count"] == 2
