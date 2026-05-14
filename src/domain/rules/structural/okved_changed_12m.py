"""OKVED_CHANGED_12M: смена основного ОКВЭД за последние 12 месяцев."""

# RULE_SOURCE: внутренние методики банков UZ; Group-IB fraud patterns
# CONFIDENCE: MEDIUM (industry practice)
# VALIDATED_BY: []

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

WINDOW_DAYS = 365


def okved_changed_12m(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    changed_at = snapshot.borrower.okved_main_changed_at
    if changed_at is None:
        return None
    days_since = (snapshot.as_of - changed_at).days
    if days_since > WINDOW_DAYS:
        return None
    return FiringEvidence(
        message=f"Основной ОКВЭД сменился {days_since} дней назад",
        message_uz=f"Asosiy ОКВЭД {days_since} kun oldin almashgan",
        evidence={"days_since_change": days_since, "current_okved": snapshot.borrower.okved_main},
    )
