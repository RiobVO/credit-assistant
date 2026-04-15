"""NEGATIVE_PROFIT_3Q: чистая прибыль ≤0 три квартала подряд."""

# RULE_SOURCE: ЦБ РУз положение №27-п; стандартная практика МСБ-кредитования
# CONFIDENCE: HIGH (regulatory)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence


def negative_profit_3q(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    quarters = sorted(snapshot.quarterly_reports, key=lambda r: r.period.end)
    if len(quarters) < 3:
        return None

    last_three = quarters[-3:]
    if any(q.net_profit.amount > Decimal("0") for q in last_three):
        return None

    return FiringEvidence(
        message="Убыток (или ноль) три квартала подряд",
        evidence={
            "profits": [str(q.net_profit.amount) for q in last_three],
            "quarters": [q.period.end.isoformat() for q in last_three],
        },
    )
