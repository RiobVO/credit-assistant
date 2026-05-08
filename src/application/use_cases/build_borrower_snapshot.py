"""build_borrower_snapshot: объединить chunks от адаптеров в BorrowerSnapshot.

Use case границы: на вход — заёмщик (заранее идентифицированный), as_of, набор
chunks от любых адаптеров. На выход — ``BorrowerSnapshot``, готовый к прогону
через ``RuleRegistry``.

Контракт:
- Все chunks обязаны иметь ``borrower_inn == borrower.inn``; иначе
  ``ChunkBorrowerMismatchError``. Это страховка от загрузки чужого файла.
- Дубликаты по периодам не разрешаются автоматически (v1 — extend, последний
  выигрывает). Конфликт-валидация добавится по реальному кейсу.
- ``loan_request`` имеет приоритет: явный аргумент → first non-None из
  ``ManualChunk``. ESF/Soliq запрос на кредит не несут.
"""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from application.dto.parsed_data_chunk import (
    EsfChunk,
    ManualChunk,
    ParsedDataChunk,
    SoliqChunk,
)
from domain.entities.borrower import Borrower
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.tax_event import TaxEvent
from domain.entities.vat_period_report import VatPeriodReport
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest


class ChunkBorrowerMismatchError(ValueError):
    """Chunk относится к другому ИНН, чем заёмщик."""

    def __init__(self, expected: INN, actual: INN, chunk_type: str) -> None:
        super().__init__(
            f"{chunk_type} attached to INN {actual.masked}, "
            f"expected {expected.masked}",
        )
        self.expected = expected
        self.actual = actual
        self.chunk_type = chunk_type


def build_borrower_snapshot(
    *,
    borrower: Borrower,
    as_of: date,
    chunks: Iterable[ParsedDataChunk],
    loan_request: LoanRequest | None = None,
) -> BorrowerSnapshot:
    annual: list[FinancialReport] = []
    quarterly: list[FinancialReport] = []
    monthly: list[MonthlyTurnover] = []
    invoices: list[Invoice] = []
    tax_events: list[TaxEvent] = []
    buyers: list[Counterparty] = []
    suppliers: list[Counterparty] = []
    buyer_share: dict[str, Decimal] = {}
    supplier_share: dict[str, Decimal] = {}
    vat_periods: list[VatPeriodReport] = []
    loan: LoanRequest | None = loan_request

    for chunk in chunks:
        _verify_borrower(borrower.inn, chunk)

        if isinstance(chunk, EsfChunk):
            invoices.extend(chunk.invoices)
        elif isinstance(chunk, SoliqChunk):
            annual.extend(chunk.annual_reports)
            quarterly.extend(chunk.quarterly_reports)
            monthly.extend(chunk.monthly_turnover)
            tax_events.extend(chunk.tax_events)
            vat_periods.extend(chunk.vat_periods)
        elif isinstance(chunk, ManualChunk):
            annual.extend(chunk.annual_reports)
            quarterly.extend(chunk.quarterly_reports)
            monthly.extend(chunk.monthly_turnover)
            invoices.extend(chunk.invoices)
            tax_events.extend(chunk.tax_events)
            buyers.extend(chunk.counterparties_buyers)
            suppliers.extend(chunk.counterparties_suppliers)
            buyer_share.update(chunk.buyer_revenue_share)
            supplier_share.update(chunk.supplier_purchase_share)
            vat_periods.extend(chunk.vat_periods)
            if loan is None and chunk.loan_request is not None:
                loan = chunk.loan_request

    return BorrowerSnapshot(
        borrower=borrower,
        as_of=as_of,
        annual_reports=annual,
        quarterly_reports=quarterly,
        monthly_turnover=monthly,
        invoices=invoices,
        tax_events=tax_events,
        counterparties_buyers=buyers,
        counterparties_suppliers=suppliers,
        buyer_revenue_share=buyer_share,
        supplier_purchase_share=supplier_share,
        vat_periods=vat_periods,
        loan_request=loan,
    )


def _verify_borrower(expected: INN, chunk: ParsedDataChunk) -> None:
    if chunk.borrower_inn != expected:
        raise ChunkBorrowerMismatchError(
            expected=expected,
            actual=chunk.borrower_inn,
            chunk_type=type(chunk).__name__,
        )
