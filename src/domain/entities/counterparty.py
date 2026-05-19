"""Counterparty: контрагент с датой регистрации для shell-company детекции."""

from dataclasses import dataclass
from datetime import date

from domain.entities.borrower import LegalForm
from domain.value_objects.inn import INN


@dataclass(frozen=True, slots=True)
class Counterparty:
    inn: INN
    name: str
    registration_date: date
    # ADR-0024 Session 3: организационно-правовая форма контрагента. None для
    # legacy payloads (до Session 3) — SHELL_COMPANY_PARTNERS трактует
    # conservative: без OPF молодой контрагент считается подозрительным.
    # `LegalForm.IE` (ИП) исключается из shell-detection: ИП регистрируется
    # за 1-2 дня без уставного капитала, молодые ИП — норма (Закон РУз
    # «О гарантиях свободы предпринимательской деятельности»).
    opf: LegalForm | None = None
    # ADR-0024 Session 3: иностранный контрагент. SINGLE_SUPPLIER_CONCENTRATION
    # эскалирует severity до high при foreign + >0.50 (FATF R.10 CDD —
    # foreign suppliers требуют усиленной проверки). Default False для
    # legacy / data sources без поля.
    is_foreign: bool = False

    def months_since_registration(self, as_of: date) -> int:
        # Полные месяцы между датами; день, месяц which has not arrived — округление вниз
        years = as_of.year - self.registration_date.year
        months = as_of.month - self.registration_date.month
        total = years * 12 + months
        if as_of.day < self.registration_date.day:
            total -= 1
        return total
