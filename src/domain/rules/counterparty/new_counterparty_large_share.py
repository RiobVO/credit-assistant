"""NEW_COUNTERPARTY_LARGE_SHARE: новые контрагенты (<180 дней) >30% оборота."""

# RULE_SOURCE: Group-IB Uzbekistan fraud report 2024-2025
# CONFIDENCE: HIGH (схема накрутки оборотов перед получением кредита)
# VALIDATED_BY: []

from datetime import timedelta
from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

NEW_COUNTERPARTY_AGE_DAYS = 180
SHARE_THRESHOLD = Decimal("0.30")


def new_counterparty_large_share(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    cutoff = snapshot.as_of - timedelta(days=NEW_COUNTERPARTY_AGE_DAYS)
    new_buyers = {
        cp.inn.value
        for cp in snapshot.counterparties_buyers
        if cp.registration_date >= cutoff
    }
    if not new_buyers:
        return None

    total_share = sum(
        (snapshot.buyer_revenue_share.get(inn, Decimal("0")) for inn in new_buyers),
        Decimal("0"),
    )
    if total_share <= SHARE_THRESHOLD:
        return None

    return FiringEvidence(
        message=f"Новые контрагенты ({len(new_buyers)}) — {total_share:.0%} выручки",
        evidence={
            "new_buyer_count": len(new_buyers),
            "new_buyer_total_share": str(total_share),
        },
    )
