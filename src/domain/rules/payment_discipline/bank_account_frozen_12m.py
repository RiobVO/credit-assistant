"""BANK_ACCOUNT_FROZEN_12M: приостановка счёта Soliq за последние 12 месяцев."""

# RULE_SOURCE: НК РУз; внутренние практики Soliq; банковский compliance
# CONFIDENCE: HIGH (regulatory)
# VALIDATED_BY: []

from datetime import timedelta

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.tax_event import TaxEventType
from domain.rules.protocol import FiringEvidence

WINDOW_DAYS = 365


def bank_account_frozen_12m(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    cutoff = snapshot.as_of - timedelta(days=WINDOW_DAYS)
    freezes = [
        ev
        for ev in snapshot.tax_events
        if ev.type == TaxEventType.ACCOUNT_FREEZE and ev.date >= cutoff
    ]
    if not freezes:
        return None

    return FiringEvidence(
        message=f"Счёт приостановлен {len(freezes)} раз за последние 12 мес",
        evidence={
            "freeze_count": len(freezes),
            "dates": [ev.date.isoformat() for ev in freezes],
        },
    )
