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
    # ADR-0024 Session 3: narrow scope для OKVED_CHANGED_12M — правило стреляет
    # только когда смена ОКЭД инициирована собственником, а не результат
    # Госкомстат auto-overwrite (массовая перекатегоризация без участия
    # заёмщика). Default False = conservative: legacy borrowers и brand-new
    # dossiers через wizard правило не fires. Заполняется парсерами FORM_1
    # (CA-DS-OKED-PARSER backlog) или вручную в UI Step 1 во flow «Пересобрать
    # с дополнениями» (требует уже известную `okved_main_changed_at`).
    # Naming: mixed-prefix `oked_changed_by_owner` рядом с existing
    # `okved_main_changed_at` — temporary до Tier 3 OKVED→ОКЭД rename
    # (ПКМ РУз №275 от 24.08.2016).
    oked_changed_by_owner: bool = False
