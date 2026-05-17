"""DIRECTOR_CHANGED_6M: смена директора за последние ~6 месяцев."""

# RULE_SOURCE: Group-IB Uzbekistan fraud report 2024-2025; внутренние методики банков
# CONFIDENCE: MEDIUM (industry practice)
# VALIDATED_BY: []

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

# 6 месяцев упрощаем как 180 дней, не calendar-точно (relativedelta — Phase 2)
WINDOW_DAYS = 180


def director_changed_6m(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    days_since = (snapshot.as_of - snapshot.borrower.director_appointed_at).days
    if days_since > WINDOW_DAYS:
        return None
    return FiringEvidence(
        message=f"Директор сменился {days_since} дней назад",
        message_uz=f"Direktor {days_since} kun oldin almashgan",
        evidence={"days_since_change": days_since},
    )
