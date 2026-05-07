"""Counterparty: контрагент с датой регистрации для shell-company детекции."""

from dataclasses import dataclass
from datetime import date

from domain.value_objects.inn import INN


@dataclass(frozen=True, slots=True)
class Counterparty:
    inn: INN
    name: str
    registration_date: date

    def months_since_registration(self, as_of: date) -> int:
        # Полные месяцы между датами; день, месяц which has not arrived — округление вниз
        years = as_of.year - self.registration_date.year
        months = as_of.month - self.registration_date.month
        total = years * 12 + months
        if as_of.day < self.registration_date.day:
            total -= 1
        return total
