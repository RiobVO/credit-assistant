"""NEW_COUNTERPARTY_LARGE_SHARE: новые контрагенты (<180 дней) дают >30% выручки."""

from datetime import date, timedelta
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.rules.counterparty.new_counterparty_large_share import (
    new_counterparty_large_share,
)
from domain.value_objects.inn import INN

AS_OF = date(2026, 5, 8)


def _snapshot(
    buyers: list[Counterparty],
    shares: dict[str, Decimal],
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
        as_of=AS_OF,
        counterparties_buyers=buyers,
        buyer_revenue_share=shares,
    )


def _cp(inn_value: str, registered_days_ago: int) -> Counterparty:
    return Counterparty(
        inn=INN(inn_value),
        name=f"ООО {inn_value}",
        registration_date=AS_OF - timedelta(days=registered_days_ago),
    )


class TestNewCounterpartyLargeShare:
    def test_fires_when_new_buyer_has_40pct(self) -> None:
        new_buyer = _cp("111111111", registered_days_ago=90)
        ev = new_counterparty_large_share(
            _snapshot([new_buyer], {"111111111": Decimal("0.40")})
        )
        assert ev is not None

    def test_silent_when_new_buyer_has_only_10pct(self) -> None:
        new_buyer = _cp("111111111", registered_days_ago=90)
        assert new_counterparty_large_share(
            _snapshot([new_buyer], {"111111111": Decimal("0.10")})
        ) is None

    def test_silent_when_buyers_are_old(self) -> None:
        old_buyer = _cp("111111111", registered_days_ago=400)
        assert new_counterparty_large_share(
            _snapshot([old_buyer], {"111111111": Decimal("0.50")})
        ) is None

    def test_aggregates_share_across_multiple_new_buyers(self) -> None:
        # Каждый по 0.20, вместе 0.40 — fires
        buyers = [_cp("111111111", 60), _cp("222222222", 30)]
        ev = new_counterparty_large_share(
            _snapshot(buyers, {"111111111": Decimal("0.20"), "222222222": Decimal("0.20")})
        )
        assert ev is not None

    def test_silent_at_exactly_30pct(self) -> None:
        new_buyer = _cp("111111111", 60)
        assert new_counterparty_large_share(
            _snapshot([new_buyer], {"111111111": Decimal("0.30")})
        ) is None

    def test_silent_with_no_buyers(self) -> None:
        assert new_counterparty_large_share(_snapshot([], {})) is None
