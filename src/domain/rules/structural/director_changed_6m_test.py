"""DIRECTOR_CHANGED_6M: смена директора в последние 6 месяцев."""

from datetime import date, timedelta

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.structural.director_changed_6m import director_changed_6m
from domain.value_objects.inn import INN

AS_OF = date(2026, 5, 8)


def _snapshot(appointed: date) -> BorrowerSnapshot:
    return BorrowerSnapshot(
        borrower=Borrower(
            inn=INN("123456789"),
            name="ООО",
            legal_form=LegalForm.LLC,
            registration_date=date(2020, 1, 1),
            director_name="Иванов",
            director_appointed_at=appointed,
            okved_main="62.01",
            registered_address="Ташкент",
        ),
        as_of=AS_OF,
    )


class TestDirectorChanged6m:
    def test_fires_when_director_appointed_30_days_ago(self) -> None:
        ev = director_changed_6m(_snapshot(AS_OF - timedelta(days=30)))
        assert ev is not None
        assert ev.evidence["days_since_change"] == 30

    def test_silent_when_director_appointed_1_year_ago(self) -> None:
        ev = director_changed_6m(_snapshot(AS_OF - timedelta(days=365)))
        assert ev is None

    def test_fires_at_boundary_180_days(self) -> None:
        # Включительно: 180 дней назад — ещё «в окне»
        ev = director_changed_6m(_snapshot(AS_OF - timedelta(days=180)))
        assert ev is not None

    def test_silent_at_181_days(self) -> None:
        ev = director_changed_6m(_snapshot(AS_OF - timedelta(days=181)))
        assert ev is None
