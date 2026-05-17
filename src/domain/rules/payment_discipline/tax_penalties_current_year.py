"""TAX_PENALTIES_CURRENT_YEAR: пеня по налогам в текущем календарном году."""

# RULE_SOURCE: НК РУз; банковская методика оценки платёжной дисциплины
# CONFIDENCE: HIGH (regulatory)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.tax_event import TaxEventType
from domain.rules.protocol import FiringEvidence


def tax_penalties_current_year(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    current_year = snapshot.as_of.year
    penalties = [
        ev
        for ev in snapshot.tax_events
        if ev.type == TaxEventType.PENALTY and ev.date.year == current_year
    ]
    if not penalties:
        return None

    total = sum(
        (ev.amount.amount for ev in penalties if ev.amount is not None),
        Decimal("0"),
    )
    count = len(penalties)
    return FiringEvidence(
        message=f"Пеня по налогам в {current_year} году: {count} шт., итого {total}",
        message_uz=f"{current_year} yilida soliq boʻyicha penyalar: {count} ta, jami {total}",
        evidence={
            "count": count,
            "total_amount": str(total),
            "year": current_year,
        },
    )
