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
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money


def _money_to_dict(m: Money | None) -> dict[str, str] | None:
    if m is None:
        return None
    return {"amount": str(m.amount), "currency": m.currency.value}


def _money_from_dict(d: dict[str, str] | None) -> Money | None:
    if d is None:
        return None
    return Money(Decimal(d["amount"]), Currency(d["currency"]))


def _financial_report_to_dict(r: FinancialReport) -> dict[str, Any]:
    return {
        "period": {"start": r.period.start.isoformat(), "end": r.period.end.isoformat()},
        "revenue": _money_to_dict(r.revenue),
        "net_profit": _money_to_dict(r.net_profit),
        "taxes_paid": _money_to_dict(r.taxes_paid),
        "vat_declared": _money_to_dict(r.vat_declared),
        "assets": _money_to_dict(r.assets),
        "liabilities": _money_to_dict(r.liabilities),
    }


def _financial_report_from_dict(d: dict[str, Any]) -> FinancialReport:
    period = DateRange(
        start=date.fromisoformat(d["period"]["start"]),
        end=date.fromisoformat(d["period"]["end"]),
    )
    revenue = _money_from_dict(d["revenue"])
    net_profit = _money_from_dict(d["net_profit"])
    taxes_paid = _money_from_dict(d["taxes_paid"])
    if revenue is None or net_profit is None or taxes_paid is None:
        raise ValueError("financial report core money fields cannot be null")
    return FinancialReport(
        period=period,
        revenue=revenue,
        net_profit=net_profit,
        taxes_paid=taxes_paid,
        vat_declared=_money_from_dict(d.get("vat_declared")),
        assets=_money_from_dict(d.get("assets")),
        liabilities=_money_from_dict(d.get("liabilities")),
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
        "esf_seller_vat_total": _money_to_dict(snapshot.esf_seller_vat_total),
        "loan_request_amount": _money_to_dict(snapshot.loan_request_amount),
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
        esf_seller_vat_total=_money_from_dict(payload.get("esf_seller_vat_total")),
        loan_request_amount=_money_from_dict(payload.get("loan_request_amount")),
    )
