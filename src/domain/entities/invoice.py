"""Invoice (ЭСФ): электронный счёт-фактура из api.faktura.uz."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from domain.value_objects.inn import INN
from domain.value_objects.money import Money


class InvoiceRole(StrEnum):
    SELLER = "seller"
    BUYER = "buyer"


@dataclass(frozen=True, slots=True)
class Invoice:
    date: date
    amount: Money
    vat_amount: Money
    our_role: InvoiceRole
    counterparty_inn: INN
    counterparty_name: str
