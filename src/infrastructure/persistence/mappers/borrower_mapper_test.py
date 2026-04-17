"""Borrower ORM-маппер: round-trip через словарь kwargs + ORM."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money
from infrastructure.persistence.mappers.borrower_mapper import (
    borrower_from_orm,
    borrower_to_orm_kwargs,
)
from infrastructure.persistence.models.borrower import BorrowerORM


def _make_borrower(*, with_capital: bool, with_okved_change: bool) -> Borrower:
    return Borrower(
        inn=INN("123456789"),
        name='ООО "Пример"',
        legal_form=LegalForm.LLC,
        registration_date=date(2018, 3, 15),
        director_name="Иванов И.И.",
        director_appointed_at=date(2022, 1, 10),
        okved_main="62.01",
        registered_address="г. Ташкент, ул. Амира Темура, 1",
        okved_main_changed_at=date(2024, 6, 1) if with_okved_change else None,
        charter_capital=Money(Decimal("50000000.00"), Currency.UZS) if with_capital else None,
    )


def _round_trip(borrower: Borrower) -> Borrower:
    kwargs = borrower_to_orm_kwargs(borrower)
    orm = BorrowerORM(**kwargs)
    return borrower_from_orm(orm)


def test_borrower_round_trip_full() -> None:
    original = _make_borrower(with_capital=True, with_okved_change=True)
    assert _round_trip(original) == original


def test_borrower_round_trip_minimal() -> None:
    # Опциональные поля None → корректно сохраняются и восстанавливаются.
    original = _make_borrower(with_capital=False, with_okved_change=False)
    restored = _round_trip(original)
    assert restored == original
    assert restored.charter_capital is None
    assert restored.okved_main_changed_at is None


def test_borrower_kwargs_no_id() -> None:
    # Mapper не должен подставлять id — он управляется репозиторием.
    borrower = _make_borrower(with_capital=True, with_okved_change=False)
    kwargs = borrower_to_orm_kwargs(borrower)
    assert "id" not in kwargs
    assert "created_at" not in kwargs
    assert "updated_at" not in kwargs
