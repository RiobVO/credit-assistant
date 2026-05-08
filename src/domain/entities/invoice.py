"""Invoice (ЭСФ): электронный счёт-фактура.

Источники: e-factura.uz CSV (без отдельной колонки НДС), Soliq XML.
VAT не хранится per-invoice — CSV-выгрузка его не содержит. Агрегированная сумма
НДС из ЭСФ передаётся через ``BorrowerSnapshot.vat_periods[*].esf_seller_vat_total``
(заполняется маппером ilova-реестра в Soliq xltx-адаптере). См. ADR 0004 + ADR 0006.
"""

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
    our_role: InvoiceRole
    counterparty_inn: INN
    counterparty_name: str
