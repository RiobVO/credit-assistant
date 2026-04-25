"""Конвертация Pydantic-схем в domain-сущности и обратно.

Изоляция: в pydantic-моделях из ``dossier_schema`` хранятся примитивы (str, int,
Decimal, date), пригодные для JSON. Domain-сущности — frozen dataclass с value
objects (INN, Money, DateRange). Этот mapper — единственное место, где
происходит conversion. Domain-слой не импортируется из interfaces, так что
обратная зависимость гарантирована отсутствием импортов pydantic из domain.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast, get_args
from uuid import UUID

from application.dto.dossier_record import DossierRecord
from application.dto.kpi_bundle import (
    KpiBundle,
    KpiUnit,
    KpiValue,
    MonthlyRevenuePoint,
)
from application.dto.parsed_data_chunk import ManualChunk
from application.use_cases.load_dossier_for_view import DossierViewBundle
from domain.entities.borrower import Borrower, LegalForm
from domain.entities.counterparty import Counterparty
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice, InvoiceRole
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.red_flag import RedFlag
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.entities.vat_period_report import VatPeriodReport
from domain.services.scoring_service import RiskScore
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money
from interfaces.api.shared.dossier_schema import (
    ApplicationOutput,
    BorrowerInput,
    BorrowerOutput,
    CounterpartyInput,
    DossierResponse,
    DossierViewResponse,
    FinancialReportInput,
    InvoiceInput,
    KpiBundleOutput,
    KpiUnitCode,
    KpiValueOutput,
    LoanRequestInput,
    ManualInputRequest,
    MoneyInput,
    MoneyOutput,
    MonthlyRevenuePointOutput,
    RecommendationCode,
    RedFlagOutput,
    RiskScoreOutput,
    SeverityCode,
    TaxEventInput,
    VatPeriodInput,
)

_VALID_SEVERITY_CODES: frozenset[str] = frozenset(get_args(SeverityCode))


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
        taxes_paid=_to_money_optional(p.taxes_paid),
        vat_declared=_to_money_optional(p.vat_declared),
        assets=_to_money_optional(p.assets),
        liabilities=_to_money_optional(p.liabilities),
        # CA-037: income statement + balance-sheet расширения.
        profit_before_tax=_to_money_optional(p.profit_before_tax),
        interest_expense=_to_money_optional(p.interest_expense),
        equity=_to_money_optional(p.equity),
        total_debt=_to_money_optional(p.total_debt),
        assets_period_start=_to_money_optional(p.assets_period_start),
        liabilities_period_start=_to_money_optional(p.liabilities_period_start),
        equity_period_start=_to_money_optional(p.equity_period_start),
        total_debt_period_start=_to_money_optional(p.total_debt_period_start),
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


def _to_vat_period(p: VatPeriodInput) -> VatPeriodReport:
    return VatPeriodReport(
        period=DateRange(p.period.start, p.period.end),
        vat_declared=_to_money_optional(p.vat_declared),
        esf_seller_vat_total=_to_money_optional(p.esf_seller_vat_total),
        submitted_at=p.submitted_at,
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
        vat_periods=[_to_vat_period(v) for v in payload.vat_periods],
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


def _to_display_score(domain_score: int) -> int:
    """Domain score (lower=better) → banking display (higher=better, 0..100).

    Phase 3.B Q1 правило A. ScoringService уже clamp'ит до 100; страхуемся
    повторно на случай будущих изменений калибровки.
    """
    return max(0, min(100, 100 - domain_score))


def risk_score_to_output(score: RiskScore) -> RiskScoreOutput:
    breakdown: dict[SeverityCode, int] = {
        sev.value: cnt for sev, cnt in score.severity_breakdown.items()
    }
    return RiskScoreOutput(
        score=score.score,
        display_score=_to_display_score(score.score),
        recommendation=score.recommendation.value,
        severity_breakdown=breakdown,
    )


def build_dossier_response(
    *,
    dossier_id: UUID,
    borrower_inn: INN,
    as_of: date,
    flags: list[RedFlag],
    score: RiskScore,
    rules_evaluated: int,
) -> DossierResponse:
    return DossierResponse(
        dossier_id=dossier_id,
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


# ---------- DossierViewResponse mapping (Phase 3.B GET /api/dossier/{id}) -----


def _money_to_output(m: Money) -> MoneyOutput:
    return MoneyOutput(amount=str(m.amount), currency=m.currency.value)


def _borrower_to_output(b: Borrower) -> BorrowerOutput:
    return BorrowerOutput(
        inn=b.inn.value,
        name=b.name,
        legal_form=b.legal_form.value,
        registration_date=b.registration_date,
        director_name=b.director_name,
        director_appointed_at=b.director_appointed_at,
        okved_main=b.okved_main,
        registered_address=b.registered_address,
        okved_main_changed_at=b.okved_main_changed_at,
        charter_capital=_money_to_output(b.charter_capital) if b.charter_capital else None,
    )


def _application_id(dossier_id: UUID, created_at: datetime) -> str:
    """Deterministic читабельный код заявки.

    Формат ``BR-YYYY-XXXX``: год создания досье + первые 4 hex-символа UUID
    (uppercase). Гарантирует, что для одного и того же dossier_id код всегда
    тот же. Уникальности XXXX в пределах года не гарантирует (16^4 ≈ 65k
    значений) — для отображения это нормально, для FK на заявку добавим
    отдельную колонку в Phase 4.
    """
    year = created_at.year
    short_hex = str(dossier_id).replace("-", "")[:4].upper()
    return f"BR-{year}-{short_hex}"


def _kpi_unit_code(unit: KpiUnit) -> KpiUnitCode:
    return unit.value


def _kpi_value_to_output(kv: KpiValue | None) -> KpiValueOutput | None:
    if kv is None:
        return None
    return KpiValueOutput(
        value=str(kv.value),
        unit=_kpi_unit_code(kv.unit),
        yoy_pct=str(kv.yoy_pct) if kv.yoy_pct is not None else None,
        sparkline=[str(p) for p in kv.sparkline],
    )


def _kpi_bundle_to_output(bundle: KpiBundle) -> KpiBundleOutput:
    return KpiBundleOutput(
        revenue_ltm=_kpi_value_to_output(bundle.revenue_ltm),
        ebit=_kpi_value_to_output(bundle.ebit),
        roe=_kpi_value_to_output(bundle.roe),
        debt_to_ebit=_kpi_value_to_output(bundle.debt_to_ebit),
    )


def _monthly_point_to_output(point: MonthlyRevenuePoint) -> MonthlyRevenuePointOutput:
    return MonthlyRevenuePointOutput(
        month=point.month_start.strftime("%Y-%m"),
        revenue=str(point.revenue),
        trend=str(point.trend),
        is_peak=point.is_peak,
    )


def _risk_score_from_record(record: DossierRecord) -> RiskScoreOutput:
    breakdown: dict[SeverityCode, int] = {
        cast(SeverityCode, sev): cnt
        for sev, cnt in record.severity_breakdown.items()
        if sev in _VALID_SEVERITY_CODES
    }
    return RiskScoreOutput(
        score=record.score,
        display_score=_to_display_score(record.score),
        recommendation=cast(RecommendationCode, record.recommendation),
        severity_breakdown=breakdown,
    )


def build_dossier_view_response(bundle: DossierViewBundle) -> DossierViewResponse:
    """Полный ответ GET /api/dossier/{id}: borrower + KPI + chart + red flags."""
    view = bundle.view
    snapshot = view.snapshot
    record = view.dossier

    return DossierViewResponse(
        dossier_id=view.dossier_id,
        borrower_inn_masked=snapshot.borrower.inn.masked,
        as_of=snapshot.as_of,
        red_flags=[red_flag_to_output(f) for f in record.red_flags],
        risk_score=_risk_score_from_record(record),
        rules_evaluated=record.rules_evaluated,
        borrower=_borrower_to_output(snapshot.borrower),
        application=ApplicationOutput(
            id=_application_id(view.dossier_id, view.created_at),
            status="in_review",
        ),
        kpis=_kpi_bundle_to_output(bundle.kpis),
        monthly_revenue_24m=[
            _monthly_point_to_output(p) for p in bundle.monthly_revenue_24m
        ],
    )
