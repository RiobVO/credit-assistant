"""Конвертация Pydantic-схем в domain-сущности и обратно.

Изоляция: в pydantic-моделях из ``dossier_schema`` хранятся примитивы (str, int,
Decimal, date), пригодные для JSON. Domain-сущности — frozen dataclass с value
objects (INN, Money, DateRange). Этот mapper — единственное место, где
происходит conversion. Domain-слой не импортируется из interfaces, так что
обратная зависимость гарантирована отсутствием импортов pydantic из domain.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from application.dto.parsed_data_chunk import ManualChunk
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.counterparty import Counterparty
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice, InvoiceRole
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.red_flag import RedFlag
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.services.scoring_service import RiskScore
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money
from interfaces.api.shared.dossier_schema import (
    BorrowerInput,
    CounterpartyInput,
    DossierResponse,
    FinancialReportInput,
    InvoiceInput,
    LoanRequestInput,
    ManualInputRequest,
    MoneyInput,
    RedFlagOutput,
    RiskScoreOutput,
    SeverityCode,
    TaxEventInput,
)


def _to_money(m: MoneyInput) -> Money:
    return Money(m.amount, Currency(m.currency))


def _to_money_optional(m: MoneyInput | None) -> Money | None:
    return _to_money(m) if m is not None else None


def to_borrower(payload: BorrowerInput) -> Borrower:
    return Borrower(
        inn=INN(payload.inn),
        name=payload.name,
        legal_form=LegalForm(payload.legal_form),
        registration_date=payload.registration_date,
        director_name=payload.director_name,
        director_appointed_at=payload.director_appointed_at,
        okved_main=payload.okved_main,
        registered_address=payload.registered_address,
        okved_main_changed_at=payload.okved_main_changed_at,
        charter_capital=_to_money_optional(payload.charter_capital),
    )


def _to_financial_report(p: FinancialReportInput) -> FinancialReport:
    return FinancialReport(
        period=DateRange(p.period.start, p.period.end),
        revenue=_to_money(p.revenue),
        net_profit=_to_money(p.net_profit),
        taxes_paid=_to_money(p.taxes_paid),
        vat_declared=_to_money_optional(p.vat_declared),
        assets=_to_money_optional(p.assets),
        liabilities=_to_money_optional(p.liabilities),
    )


def _to_invoice(p: InvoiceInput) -> Invoice:
    return Invoice(
        date=p.date,
        amount=_to_money(p.amount),
        our_role=InvoiceRole(p.our_role),
        counterparty_inn=INN(p.counterparty_inn),
        counterparty_name=p.counterparty_name,
    )


def _to_counterparty(p: CounterpartyInput) -> Counterparty:
    return Counterparty(
        inn=INN(p.inn),
        name=p.name,
        registration_date=p.registration_date,
    )


def _to_loan_request(p: LoanRequestInput | None) -> LoanRequest | None:
    if p is None:
        return None
    return LoanRequest(
        amount=_to_money(p.amount),
        term_months=p.term_months,
        rate_pct=p.rate_pct,
        purpose=p.purpose,
        category=p.category,
    )


def _to_tax_event(p: TaxEventInput) -> TaxEvent:
    return TaxEvent(
        date=p.date,
        type=TaxEventType(p.type),
        amount=_to_money_optional(p.amount),
        delay_days=p.delay_days,
        duration_days=p.duration_days,
    )


def to_manual_chunk(payload: ManualInputRequest, borrower_inn: INN) -> ManualChunk:
    return ManualChunk(
        borrower_inn=borrower_inn,
        annual_reports=[_to_financial_report(r) for r in payload.annual_reports],
        quarterly_reports=[_to_financial_report(r) for r in payload.quarterly_reports],
        monthly_turnover=[
            MonthlyTurnover(
                month_start=t.month_start,
                revenue=_to_money(t.revenue),
                vat_obligations=_to_money_optional(t.vat_obligations),
            )
            for t in payload.monthly_turnover
        ],
        invoices=[_to_invoice(i) for i in payload.invoices],
        tax_events=[_to_tax_event(e) for e in payload.tax_events],
        counterparties_buyers=[_to_counterparty(c) for c in payload.counterparties_buyers],
        counterparties_suppliers=[
            _to_counterparty(c) for c in payload.counterparties_suppliers
        ],
        buyer_revenue_share={s.inn: s.share for s in payload.buyer_revenue_share},
        supplier_purchase_share={
            s.inn: s.share for s in payload.supplier_purchase_share
        },
        loan_request=_to_loan_request(payload.loan_request),
    )


def red_flag_to_output(flag: RedFlag) -> RedFlagOutput:
    return RedFlagOutput(
        rule_id=flag.rule_id,
        rule_version=flag.rule_version,
        severity=flag.severity.value,
        source=flag.source,
        message=flag.message,
        evidence=_jsonable_dict(flag.evidence),
        detected_at=flag.detected_at,
    )


def risk_score_to_output(score: RiskScore) -> RiskScoreOutput:
    breakdown: dict[SeverityCode, int] = {
        sev.value: cnt for sev, cnt in score.severity_breakdown.items()
    }
    return RiskScoreOutput(
        score=score.score,
        recommendation=score.recommendation.value,
        severity_breakdown=breakdown,
    )


def build_dossier_response(
    *,
    borrower_inn: INN,
    as_of: date,
    flags: list[RedFlag],
    score: RiskScore,
    rules_evaluated: int,
) -> DossierResponse:
    return DossierResponse(
        borrower_inn_masked=borrower_inn.masked,
        as_of=as_of,
        red_flags=[red_flag_to_output(f) for f in flags],
        risk_score=risk_score_to_output(score),
        rules_evaluated=rules_evaluated,
    )


def _jsonable(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _jsonable_dict(d: dict[str, Any]) -> dict[str, Any]:
    return {k: _jsonable(v) for k, v in d.items()}
