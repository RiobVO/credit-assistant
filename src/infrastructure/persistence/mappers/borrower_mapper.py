"""Borrower ↔ BorrowerORM. Money разложен на amount + currency."""

from __future__ import annotations

from typing import Any

from domain.entities.borrower import Borrower, LegalForm
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money
from infrastructure.persistence.models.borrower import BorrowerORM


def borrower_to_orm_kwargs(borrower: Borrower) -> dict[str, Any]:
    """Возвращает kwargs для INSERT/ON CONFLICT UPDATE — без id и audit-полей."""
    kwargs: dict[str, Any] = {
        "inn": borrower.inn.value,
        "name": borrower.name,
        "legal_form": borrower.legal_form.value,
        "registration_date": borrower.registration_date,
        "director_name": borrower.director_name,
        "director_appointed_at": borrower.director_appointed_at,
        "okved_main": borrower.okved_main,
        "registered_address": borrower.registered_address,
        "okved_main_changed_at": borrower.okved_main_changed_at,
    }
    if borrower.charter_capital is not None:
        kwargs["charter_capital_amount"] = borrower.charter_capital.amount
        kwargs["charter_capital_currency"] = borrower.charter_capital.currency.value
    else:
        kwargs["charter_capital_amount"] = None
        kwargs["charter_capital_currency"] = None
    return kwargs


def borrower_from_orm(orm: BorrowerORM) -> Borrower:
    charter_capital: Money | None = None
    if orm.charter_capital_amount is not None and orm.charter_capital_currency is not None:
        charter_capital = Money(orm.charter_capital_amount, Currency(orm.charter_capital_currency))
    return Borrower(
        inn=INN(orm.inn),
        name=orm.name,
        legal_form=LegalForm(orm.legal_form),
        registration_date=orm.registration_date,
        director_name=orm.director_name,
        director_appointed_at=orm.director_appointed_at,
        okved_main=orm.okved_main,
        registered_address=orm.registered_address,
        okved_main_changed_at=orm.okved_main_changed_at,
        charter_capital=charter_capital,
    )
