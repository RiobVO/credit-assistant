"""CASH_FLOW_QUALITY: OCF < 50% net profit (ADR-0024 Session 2)."""

# RULE_SOURCE: IFC SME Banking Knowledge Guide ch.4 «Cash Flow Analysis»;
#   стандартная accrual-vs-cash quality analysis (Beneish M-score 1999,
#   Healy & Wahlen «A Review of the Earnings Management Literature» 1999).
# CONFIDENCE: HIGH (multilateral SME methodology + academic standard)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

OCF_TO_NET_PROFIT_FLOOR = Decimal("0.50")


def cash_flow_quality(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    """Срабатывает когда OCF < 50% net_profit (низкое качество прибыли).

    OCF (operating cash flow) — фактический cash сгенерированный операциями.
    Net profit — accrual прибыль, может содержать non-cash items (D&A,
    accrued revenues, provisions, переоценки запасов). Когда OCF существенно
    ниже net profit — «прибыль на бумаге» не подкреплена реальным cash flow.
    Сигнал earnings manipulation или агрессивного revenue recognition
    (Beneish M-score 1999, Healy & Wahlen JIFM 1999).

    * `annual_reports` пуст → None.
    * `latest.operating_cash_flow` None → None (silent: нет OCF, не сигнал).
    * `net_profit ≤ 0` → None (убыток или ноль — ratio не имеет смысла,
      эту ситуацию ловит NEGATIVE_PROFIT_3Q).
    * `OCF / net_profit ≥ 0.50` → None.
    * иначе → fires.

    Boundary inclusive на 0.50: ratio = 0.50 → silent (на грани, не fires).
    Источник: IFC SME Banking Knowledge Guide ch.4.
    """
    if not snapshot.annual_reports:
        return None
    latest = max(snapshot.annual_reports, key=lambda r: r.period.end)
    if latest.operating_cash_flow is None:
        return None
    net_profit = latest.net_profit.amount
    if net_profit <= Decimal(0):
        return None
    ocf = latest.operating_cash_flow.amount
    ratio = ocf / net_profit
    if ratio >= OCF_TO_NET_PROFIT_FLOOR:
        return None

    ratio_rounded = ratio.quantize(Decimal("0.01"))
    ratio_str = str(ratio_rounded).replace(".", ",")
    return FiringEvidence(
        message=(
            f"OCF/Net Profit = {ratio_str} (<0,50) — прибыль не подкреплена "
            "операционным cash flow"
        ),
        message_uz=(
            f"OCF/Sof foyda = {ratio_str} (<0,50) — foyda operatsion pul "
            "oqimi bilan taʼminlanmagan"
        ),
        evidence={
            "operating_cash_flow": str(ocf.quantize(Decimal("1"))),
            "net_profit": str(net_profit.quantize(Decimal("1"))),
            "ocf_to_net_profit": str(ratio_rounded),
            "year": str(latest.period.end.year),
        },
    )
