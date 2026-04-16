"""ParsedDataChunk: единица данных, которую возвращает любой data adapter.

Каждый адаптер (ESF CSV, Soliq Excel, ManualInput) собирает свой подтип chunk
и возвращает его в use case ``build_borrower_snapshot``. Use case проверяет, что
``borrower_inn`` всех chunks совпадает с заёмщиком, и сливает поля в общий
``BorrowerSnapshot``.

Граница типов: chunks несут *исходные* (raw) данные адаптера; aggregation, slicing
по периодам и расчёт долей делает use case или domain. Адаптер не знает про
структуру snapshot, кроме своего chunk-типа.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from domain.entities.counterparty import Counterparty
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.tax_event import TaxEvent
from domain.value_objects.inn import INN
from domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class EsfChunk:
    """Выход парсера ЭСФ (e-factura.uz CSV / Soliq XML).

    Несёт только сырые invoices. Агрегаты (buyer_revenue_share и контрагенты как
    сущности) считает use case или отдельный counterparty-adapter, у которого
    есть даты регистрации из открытого реестра.
    """

    borrower_inn: INN
    invoices: list[Invoice] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SoliqChunk:
    """Выход парсера Soliq Excel / выписок личного кабинета.

    Сюда же приходит агрегат ``esf_seller_vat_total`` от VAT-адаптера (см. ADR
    0004). Технически это отдельный источник, но в Phase 2 объединяем — оба
    приходят из my3.soliq.uz.
    """

    borrower_inn: INN
    annual_reports: list[FinancialReport] = field(default_factory=list)
    quarterly_reports: list[FinancialReport] = field(default_factory=list)
    monthly_turnover: list[MonthlyTurnover] = field(default_factory=list)
    tax_events: list[TaxEvent] = field(default_factory=list)
    esf_seller_vat_total: Money | None = None


@dataclass(frozen=True, slots=True)
class ManualChunk:
    """Выход API ручного ввода (банк-аналитик или бухгалтер заполняет форму).

    Покрывает поля, которых нет в автоматических источниках: контрагенты с долями,
    запрашиваемая сумма кредита. Финансовые отчёты тоже принимаются — fallback
    для случаев, когда выгрузка Soliq недоступна.
    """

    borrower_inn: INN
    annual_reports: list[FinancialReport] = field(default_factory=list)
    quarterly_reports: list[FinancialReport] = field(default_factory=list)
    monthly_turnover: list[MonthlyTurnover] = field(default_factory=list)
    invoices: list[Invoice] = field(default_factory=list)
    tax_events: list[TaxEvent] = field(default_factory=list)
    counterparties_buyers: list[Counterparty] = field(default_factory=list)
    counterparties_suppliers: list[Counterparty] = field(default_factory=list)
    buyer_revenue_share: dict[str, Decimal] = field(default_factory=dict)
    supplier_purchase_share: dict[str, Decimal] = field(default_factory=dict)
    loan_request_amount: Money | None = None


ParsedDataChunk = EsfChunk | SoliqChunk | ManualChunk
