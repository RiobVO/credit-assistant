"""SINGLE_BUYER_CONCENTRATION: >70% выручки на одном покупателе."""

# RULE_SOURCE: Базель III concentration risk; внутренние методики Kapitalbank
# CONFIDENCE: HIGH (industry-standard concentration risk)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

THRESHOLD = Decimal("0.70")


def single_buyer_concentration(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    if not snapshot.buyer_revenue_share:
        return None
    max_inn, max_share = max(snapshot.buyer_revenue_share.items(), key=lambda x: x[1])
    if max_share <= THRESHOLD:
        return None
    return FiringEvidence(
        message=f"Один покупатель = {max_share:.0%} выручки",
        evidence={
            "max_buyer_inn": max_inn,
            "max_buyer_share": str(max_share),
        },
    )
