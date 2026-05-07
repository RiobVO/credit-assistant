"""OKVED_CHANGED_12M: смена основного вида деятельности за последние 12 мес."""

from datetime import date, timedelta

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.structural.okved_changed_12m import okved_changed_12m
from domain.value_objects.inn import INN

AS_OF = date(2026, 5, 8)


def _snapshot(okved_changed_at: date | None) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=Borrower(
            inn=INN("123456789"),
            name="ООО",
            legal_form=LegalForm.LLC,
            registration_date=date(2020, 1, 1),
            director_name="Иванов",
            director_appointed_at=date(2020, 1, 1),
            okved_main="62.01",
            okved_main_changed_at=okved_changed_at,
            registered_address="Ташкент",
        ),
        as_of=AS_OF,
    )


class TestOkvedChanged12m:
    def test_fires_when_okved_changed_100_days_ago(self) -> None:
        ev = okved_changed_12m(_snapshot(AS_OF - timedelta(days=100)))
        assert ev is not None

    def test_silent_when_okved_changed_400_days_ago(self) -> None:
        assert okved_changed_12m(_snapshot(AS_OF - timedelta(days=400))) is None

    def test_silent_when_no_change_recorded(self) -> None:
        assert okved_changed_12m(_snapshot(None)) is None

    def test_fires_at_boundary_365_days(self) -> None:
        ev = okved_changed_12m(_snapshot(AS_OF - timedelta(days=365)))
        assert ev is not None
