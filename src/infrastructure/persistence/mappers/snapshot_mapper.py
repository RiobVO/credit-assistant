"""BorrowerSnapshot ↔ JSONB-payload.

Сериализация детерминирована и обратима без потерь:
- Decimal → str (JSON float теряет точность)
- date → ISO 8601
- enum → .value
- INN → .value (при чтении валидируется обратно)
- None пробрасывается как null

Borrower не входит в payload — он хранится отдельно через FK borrower_id.
В ``snapshot_from_payload`` borrower инжектится снаружи (репозиторий делает join).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, cast

from domain.entities.borrower import Borrower
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.entities.financial_report import FinancialReport
from domain.entities.invoice import Invoice, InvoiceRole
from domain.entities.monthly_turnover import MonthlyTurnover
from domain.entities.tax_event import TaxEvent, TaxEventType
from domain.entities.vat_period_report import VatPeriodReport
from domain.value_objects.balance_snapshot import BalanceSnapshot
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.loan_request import LoanRequest
from domain.value_objects.money import Currency, Money


def _loan_request_to_dict(lr: LoanRequest | None) -> dict[str, Any] | None:
    if lr is None:
        return None
    return {
        "amount": _money_to_dict(lr.amount),
        "term_months": lr.term_months,
        "rate_pct": str(lr.rate_pct),
        "purpose": lr.purpose,
        "category": lr.category,
    }


def _loan_request_from_dict(d: dict[str, Any] | None) -> LoanRequest | None:
    if d is None:
        return None
    amount = _money_from_dict(d["amount"])
    if amount is None:
        raise ValueError("loan_request.amount cannot be null")
    return LoanRequest(
        amount=amount,
        term_months=int(d["term_months"]),
        rate_pct=Decimal(d["rate_pct"]),
        purpose=d["purpose"],
        category=d["category"],
    )


def _money_to_dict(m: Money | None) -> dict[str, str] | None:
    if m is None:
        return None
    return {"amount": str(m.amount), "currency": m.currency.value}


def _money_from_dict(d: dict[str, str] | None) -> Money | None:
    if d is None:
        return None
    return Money(Decimal(d["amount"]), Currency(d["currency"]))


def _financial_report_to_dict(r: FinancialReport) -> dict[str, Any]:
    # CA-047: JSONB-формат остаётся flat (8 balance-полей на верхнем уровне) —
    # legacy записи в БД (до CA-047) читаются без миграции. Группировка в
    # BalanceSnapshot — только domain-уровень; разворачиваем обратно при
    # сериализации.
    end = r.balance_end or BalanceSnapshot()
    start = r.balance_start or BalanceSnapshot()
    return {
        "period": {"start": r.period.start.isoformat(), "end": r.period.end.isoformat()},
        "revenue": _money_to_dict(r.revenue),
        "net_profit": _money_to_dict(r.net_profit),
        "taxes_paid": _money_to_dict(r.taxes_paid),
        "vat_declared": _money_to_dict(r.vat_declared),
        "assets": _money_to_dict(end.assets),
        "liabilities": _money_to_dict(end.liabilities),
        "profit_before_tax": _money_to_dict(r.profit_before_tax),
        "interest_expense": _money_to_dict(r.interest_expense),
        "equity": _money_to_dict(end.equity),
        "total_debt": _money_to_dict(end.total_debt),
        "assets_period_start": _money_to_dict(start.assets),
        "liabilities_period_start": _money_to_dict(start.liabilities),
        "equity_period_start": _money_to_dict(start.equity),
        "total_debt_period_start": _money_to_dict(start.total_debt),
    }


def _financial_report_from_dict(d: dict[str, Any]) -> FinancialReport:
    period = DateRange(
        start=date.fromisoformat(d["period"]["start"]),
        end=date.fromisoformat(d["period"]["end"]),
    )
    revenue = _money_from_dict(d["revenue"])
    net_profit = _money_from_dict(d["net_profit"])
    # CA-044: taxes_paid стал опциональным. Legacy записи (до CA-044) хранили
    # его как обязательное поле; новые могут не содержать ключа вовсе.
    if revenue is None or net_profit is None:
        raise ValueError("financial report revenue/net_profit cannot be null")
    # CA-047: собираем BalanceSnapshot из flat-ключей JSONB. Пустой snapshot
    # (все 4 None) → None, чтобы readers не разделяли «нет данных» vs «есть
    # snapshot со всеми None» — семантически одно и то же.
    balance_end = BalanceSnapshot(
        assets=_money_from_dict(d.get("assets")),
        liabilities=_money_from_dict(d.get("liabilities")),
        equity=_money_from_dict(d.get("equity")),
        total_debt=_money_from_dict(d.get("total_debt")),
    )
    balance_start = BalanceSnapshot(
        assets=_money_from_dict(d.get("assets_period_start")),
        liabilities=_money_from_dict(d.get("liabilities_period_start")),
        equity=_money_from_dict(d.get("equity_period_start")),
        total_debt=_money_from_dict(d.get("total_debt_period_start")),
    )
    return FinancialReport(
        period=period,
        revenue=revenue,
        net_profit=net_profit,
        taxes_paid=_money_from_dict(d.get("taxes_paid")),
        vat_declared=_money_from_dict(d.get("vat_declared")),
        # CA-037: income-statement nullable поля; `.get()` без default → None
        # для legacy записей до CA-037.
        profit_before_tax=_money_from_dict(d.get("profit_before_tax")),
        interest_expense=_money_from_dict(d.get("interest_expense")),
        balance_end=balance_end if not balance_end.is_empty() else None,
        balance_start=balance_start if not balance_start.is_empty() else None,
    )


def _monthly_turnover_to_dict(m: MonthlyTurnover) -> dict[str, Any]:
    return {
        "month_start": m.month_start.isoformat(),
        "revenue": _money_to_dict(m.revenue),
        "vat_obligations": _money_to_dict(m.vat_obligations),
    }


def _monthly_turnover_from_dict(d: dict[str, Any]) -> MonthlyTurnover:
    revenue = _money_from_dict(d["revenue"])
    if revenue is None:
        raise ValueError("monthly turnover revenue cannot be null")
    return MonthlyTurnover(
        month_start=date.fromisoformat(d["month_start"]),
        revenue=revenue,
        vat_obligations=_money_from_dict(d.get("vat_obligations")),
    )


def _counterparty_to_dict(c: Counterparty) -> dict[str, Any]:
    return {
        "inn": c.inn.value,
        "name": c.name,
        "registration_date": c.registration_date.isoformat(),
    }


def _counterparty_from_dict(d: dict[str, Any]) -> Counterparty:
    return Counterparty(
        inn=INN(d["inn"]),
        name=d["name"],
        registration_date=date.fromisoformat(d["registration_date"]),
    )


def _invoice_to_dict(inv: Invoice) -> dict[str, Any]:
    return {
        "date": inv.date.isoformat(),
        "amount": _money_to_dict(inv.amount),
        "our_role": inv.our_role.value,
        "counterparty_inn": inv.counterparty_inn.value,
        "counterparty_name": inv.counterparty_name,
    }


def _invoice_from_dict(d: dict[str, Any]) -> Invoice:
    amount = _money_from_dict(d["amount"])
    if amount is None:
        raise ValueError("invoice amount cannot be null")
    return Invoice(
        date=date.fromisoformat(d["date"]),
        amount=amount,
        our_role=InvoiceRole(d["our_role"]),
        counterparty_inn=INN(d["counterparty_inn"]),
        counterparty_name=d["counterparty_name"],
    )


def _tax_event_to_dict(t: TaxEvent) -> dict[str, Any]:
    return {
        "date": t.date.isoformat(),
        "type": t.type.value,
        "amount": _money_to_dict(t.amount),
        "delay_days": t.delay_days,
        "duration_days": t.duration_days,
    }


def _tax_event_from_dict(d: dict[str, Any]) -> TaxEvent:
    return TaxEvent(
        date=date.fromisoformat(d["date"]),
        type=TaxEventType(d["type"]),
        amount=_money_from_dict(d.get("amount")),
        delay_days=d.get("delay_days"),
        duration_days=d.get("duration_days"),
    )


def _vat_period_to_dict(p: VatPeriodReport) -> dict[str, Any]:
    return {
        "period": {"start": p.period.start.isoformat(), "end": p.period.end.isoformat()},
        "vat_declared": _money_to_dict(p.vat_declared),
        "esf_seller_vat_total": _money_to_dict(p.esf_seller_vat_total),
        "submitted_at": p.submitted_at.isoformat() if p.submitted_at is not None else None,
    }


def _vat_period_from_dict(d: dict[str, Any]) -> VatPeriodReport:
    submitted_raw = d.get("submitted_at")
    return VatPeriodReport(
        period=DateRange(
            start=date.fromisoformat(d["period"]["start"]),
            end=date.fromisoformat(d["period"]["end"]),
        ),
        vat_declared=_money_from_dict(d.get("vat_declared")),
        esf_seller_vat_total=_money_from_dict(d.get("esf_seller_vat_total")),
        submitted_at=date.fromisoformat(submitted_raw) if submitted_raw is not None else None,
    )


def snapshot_to_payload(snapshot: BorrowerSnapshot) -> dict[str, Any]:
    """Сериализует snapshot в JSONB-совместимый dict (без borrower)."""
    return {
        "as_of": snapshot.as_of.isoformat(),
        "annual_reports": [_financial_report_to_dict(r) for r in snapshot.annual_reports],
        "quarterly_reports": [_financial_report_to_dict(r) for r in snapshot.quarterly_reports],
        "monthly_turnover": [_monthly_turnover_to_dict(m) for m in snapshot.monthly_turnover],
        "counterparties_buyers": [
            _counterparty_to_dict(c) for c in snapshot.counterparties_buyers
        ],
        "counterparties_suppliers": [
            _counterparty_to_dict(c) for c in snapshot.counterparties_suppliers
        ],
        "buyer_revenue_share": {k: str(v) for k, v in snapshot.buyer_revenue_share.items()},
        "supplier_purchase_share": {
            k: str(v) for k, v in snapshot.supplier_purchase_share.items()
        },
        "invoices": [_invoice_to_dict(i) for i in snapshot.invoices],
        "tax_events": [_tax_event_to_dict(t) for t in snapshot.tax_events],
        "vat_periods": [_vat_period_to_dict(p) for p in snapshot.vat_periods],
        "loan_request": _loan_request_to_dict(snapshot.loan_request),
    }


def snapshot_from_payload(payload: dict[str, Any], borrower: Borrower) -> BorrowerSnapshot:
    """Восстанавливает snapshot из JSONB; borrower инжектится снаружи (по FK)."""
    return BorrowerSnapshot(
        borrower=borrower,
        as_of=date.fromisoformat(payload["as_of"]),
        annual_reports=[_financial_report_from_dict(d) for d in payload["annual_reports"]],
        quarterly_reports=[
            _financial_report_from_dict(d) for d in payload["quarterly_reports"]
        ],
        monthly_turnover=[
            _monthly_turnover_from_dict(d) for d in payload["monthly_turnover"]
        ],
        counterparties_buyers=[
            _counterparty_from_dict(d) for d in payload["counterparties_buyers"]
        ],
        counterparties_suppliers=[
            _counterparty_from_dict(d) for d in payload["counterparties_suppliers"]
        ],
        buyer_revenue_share={
            k: Decimal(v) for k, v in cast(dict[str, str], payload["buyer_revenue_share"]).items()
        },
        supplier_purchase_share={
            k: Decimal(v)
            for k, v in cast(dict[str, str], payload["supplier_purchase_share"]).items()
        },
        invoices=[_invoice_from_dict(d) for d in payload["invoices"]],
        tax_events=[_tax_event_from_dict(d) for d in payload["tax_events"]],
        vat_periods=[_vat_period_from_dict(d) for d in payload.get("vat_periods", [])],
        loan_request=_loan_request_from_dict(payload.get("loan_request")),
    )
