"""DIRECTOR_CHANGED_6M: смена директора в последние 6 месяцев + материальная заявка."""

from datetime import date, timedelta
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.structural.director_changed_6m import director_changed_6m
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money

UZS = Currency.UZS
AS_OF = date(2026, 5, 8)


def _loan(amount: int = 700_000_000) -> LoanRequest:
    """Default loan ≥500 млн UZS — выше ADR-0024 материального порога."""
    return LoanRequest(
        amount=Money(Decimal(amount), UZS),
        term_months=24,
        rate_pct=Decimal("22.5"),
        purpose="working_capital",
        category="standard",
    )


_DEFAULT_LOAN_SENTINEL: LoanRequest = LoanRequest(
    amount=Money(Decimal(1), UZS),
    term_months=1,
    rate_pct=Decimal("0"),
    purpose="__sentinel__",
    category="__sentinel__",
)


def _snapshot(
    appointed: date,
    *,
    loan: LoanRequest | None = _DEFAULT_LOAN_SENTINEL,
) -> BorrowerSnapshot:
    # Sentinel-семантика: parameter не передан → дефолтный материальный loan.
    # Явный None → no loan_request в snapshot. LoanRequest != None → как передан.
    actual_loan: LoanRequest | None = (
        _loan() if loan is _DEFAULT_LOAN_SENTINEL else loan
    )
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
        loan_request=actual_loan,
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

    def test_silent_when_no_loan_request(self) -> None:
        # ADR-0024: смена директора без активной заявки = operational change
        ev = director_changed_6m(_snapshot(AS_OF - timedelta(days=30), loan=None))
        assert ev is None

    def test_silent_when_loan_below_material_threshold(self) -> None:
        # ADR-0024: ≥500 млн UZS — материальный порог. 400 млн → silent.
        ev = director_changed_6m(
            _snapshot(AS_OF - timedelta(days=30), loan=_loan(amount=400_000_000))
        )
        assert ev is None

    def test_fires_at_material_threshold(self) -> None:
        # 500 млн ровно — fires (boundary inclusive: >=)
        ev = director_changed_6m(
            _snapshot(AS_OF - timedelta(days=30), loan=_loan(amount=500_000_000))
        )
        assert ev is not None
