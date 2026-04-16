"""TAX_PAYMENT_DELAYS: задержки уплаты налогов >30 дней."""

# RULE_SOURCE: НК РУз; внутренние методики Soliq + банковская практика
# CONFIDENCE: HIGH (regulatory + tax authority practice)
# VALIDATED_BY: []

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.tax_event import TaxEventType
from domain.rules.protocol import FiringEvidence

THRESHOLD_DAYS = 30


def tax_payment_delays(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    delayed = [
        ev
        for ev in snapshot.tax_events
        if ev.type == TaxEventType.PAYMENT
        and ev.delay_days is not None
        and ev.delay_days > THRESHOLD_DAYS
    ]
    if not delayed:
        return None

    max_delay = max(ev.delay_days for ev in delayed if ev.delay_days is not None)
    return FiringEvidence(
        message=f"Задержки уплаты налогов: {len(delayed)} шт., макс {max_delay} дней",
        evidence={
            "delayed_count": len(delayed),
            "max_delay_days": max_delay,
        },
    )
