"""Counterparty: контрагент с ИНН и датой регистрации (для shell-company детекции)."""

from datetime import date

from domain.entities.counterparty import Counterparty
from domain.value_objects.inn import INN


def _cp(reg: date) -> Counterparty:
    return Counterparty(
        inn=INN("987654321"),
        name="ООО Контрагент",
        registration_date=reg,
    )


class TestCounterpartyConstruction:
    def test_creates_with_required_fields(self) -> None:
        cp = _cp(date(2020, 1, 1))
        assert cp.inn.value == "987654321"
        assert cp.name == "ООО Контрагент"


class TestCounterpartyAge:
    def test_months_since_registration_full_year(self) -> None:
        cp = _cp(date(2025, 5, 8))
        assert cp.months_since_registration(date(2026, 5, 8)) == 12

    def test_months_since_registration_six_months(self) -> None:
        # Граничное значение для SHELL_COMPANY_PARTNERS правила
        cp = _cp(date(2025, 11, 8))
        assert cp.months_since_registration(date(2026, 5, 8)) == 6

    def test_months_since_registration_partial_month(self) -> None:
        # 9 января - 8 мая того же года: 3 полных месяца + 30 дней → 3
        cp = _cp(date(2026, 1, 9))
        assert cp.months_since_registration(date(2026, 5, 8)) == 3
