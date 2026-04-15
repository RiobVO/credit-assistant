"""BorrowerSnapshot: вход для всех правил red-flag engine.

Адаптеры (Phase 2) формируют snapshot из raw-источников (Soliq Excel, ЭСФ JSON, ручной ввод).
Правила работают только с этим типом, ничего не зная о форматах источников.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower
from domain.entities.counterparty import Counterparty
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.tax_event import TaxEvent
from domain.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class BorrowerSnapshot:
    borrower: Borrower
    as_of: date

    annual_reports: list[FinancialReport] = field(default_factory=list)
    quarterly_reports: list[FinancialReport] = field(default_factory=list)
    monthly_turnover: list[MonthlyTurnover] = field(default_factory=list)

    counterparties_buyers: list[Counterparty] = field(default_factory=list)
    counterparties_suppliers: list[Counterparty] = field(default_factory=list)
    # Доля контрагента в выручке/закупках, ключ — INN.value
    buyer_revenue_share: dict[str, Decimal] = field(default_factory=dict)
    supplier_purchase_share: dict[str, Decimal] = field(default_factory=dict)

    invoices: list[Invoice] = field(default_factory=list)
    tax_events: list[TaxEvent] = field(default_factory=list)

    loan_request_amount: Money | None = None
