"""SINGLE_SUPPLIER_CONCENTRATION: >60% закупок у одного поставщика."""

# RULE_SOURCE: Базель III concentration risk; supply-chain risk practice
# CONFIDENCE: HIGH (industry-standard)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

THRESHOLD = Decimal("0.60")


def single_supplier_concentration(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    if not snapshot.supplier_purchase_share:
        return None
    max_inn, max_share = max(snapshot.supplier_purchase_share.items(), key=lambda x: x[1])
    if max_share <= THRESHOLD:
        return None
    return FiringEvidence(
        message=f"Один поставщик = {max_share:.0%} закупок",
        message_uz=f"Bitta yetkazib beruvchi = xaridlarning {max_share:.0%}",
        evidence={
            "max_supplier_inn": max_inn,
            "max_supplier_share": str(max_share),
        },
    )
