"""Borrower: юрлицо/ИП — заёмщик банка."""

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money


def _llc() -> Borrower:
    return Borrower(
        inn=INN("123456789"),
        name='ООО "Тестовая фирма"',
        legal_form=LegalForm.LLC,
        registration_date=date(2020, 3, 15),
        director_name="Иванов И.И.",
        director_appointed_at=date(2024, 1, 10),
        okved_main="62.01",
        registered_address="г. Ташкент, ул. Амира Темура 1",
        charter_capital=Money(Decimal("400000000"), Currency.UZS),
    )


class TestLegalForm:
    def test_includes_uzbek_forms(self) -> None:
        assert LegalForm.LLC.value == "llc"
        assert LegalForm.IE.value == "ie"
        assert LegalForm.JSC.value == "jsc"


class TestBorrowerConstruction:
    def test_creates_with_required_fields(self) -> None:
        b = _llc()
        assert b.inn.value == "123456789"
        assert b.legal_form == LegalForm.LLC

    def test_okved_changed_at_defaults_to_none(self) -> None:
        b = _llc()
        assert b.okved_main_changed_at is None

    def test_individual_entrepreneur_with_14_digit_inn(self) -> None:
        ie = Borrower(
            inn=INN("12345678901234"),
            name="ИП Петров",
            legal_form=LegalForm.IE,
            registration_date=date(2023, 1, 1),
            director_name="Петров П.П.",
            director_appointed_at=date(2023, 1, 1),
            okved_main="47.11",
            registered_address="Ташкент",
        )
        assert ie.legal_form == LegalForm.IE
