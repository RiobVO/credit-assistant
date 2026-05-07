"""Borrower: заёмщик банка — юрлицо или ИП Узбекистана."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from domain.value_objects.inn import INN
from domain.value_objects.money import Money


class LegalForm(StrEnum):
    LLC = "llc"  # ООО / МЧЖ
    PE = "pe"  # Частное предприятие
    LTD = "ltd"
    JSC = "jsc"  # АО
    IE = "ie"  # Индивидуальный предприниматель
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Borrower:
    inn: INN
    name: str
    legal_form: LegalForm
    registration_date: date
    director_name: str
    director_appointed_at: date
    okved_main: str
    registered_address: str
    okved_main_changed_at: date | None = None
    charter_capital: Money | None = None
