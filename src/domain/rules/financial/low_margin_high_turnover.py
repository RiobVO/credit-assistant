"""LOW_MARGIN_HIGH_TURNOVER: маржа <5% при годовой выручке >5 млрд сум."""

# RULE_SOURCE: внутренние методики UZ-банков; стандартная МСБ-практика
# CONFIDENCE: MEDIUM (industry practice)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

TURNOVER_THRESHOLD = Decimal("5000000000")  # 5 млрд UZS
MARGIN_THRESHOLD = Decimal("0.05")  # 5%


def low_margin_high_turnover(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    if not snapshot.annual_reports:
        return None
    latest = max(snapshot.annual_reports, key=lambda r: r.period.end)

    revenue = latest.revenue.amount
    if revenue <= TURNOVER_THRESHOLD:
        return None

    margin = latest.net_profit.amount / revenue
    if margin >= MARGIN_THRESHOLD:
        return None

    # Decimal-деление двух integer-like значений даёт хвост в 20+ знаков
    # (см. CA-021b: было 0.02160653715822424767 в evidence PDF).
    margin_rounded = margin.quantize(Decimal("0.0001"))
    return FiringEvidence(
        message=f"Маржа {margin:.1%} при годовой выручке {revenue}",
        evidence={
            "revenue": str(revenue),
            "net_profit": str(latest.net_profit.amount),
            "margin": str(margin_rounded),
        },
    )
