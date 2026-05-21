"""TAX_PENALTIES_CURRENT_YEAR: материальная пеня по налогам в текущем календарном году.

ADR-0024 Session 3: правило фильтрует пени по `TaxEvent.material`. Только
material=True (ст.223 НК РУз — сокрытие налоговой базы, штраф 20% от суммы)
триггерит правило. material=False (ст.219 КоАО — просрочка отчёта,
БРВ-штраф / процедурные нарушения) игнорируется — это операционная
неаккуратность, не AML/credit-risk сигнал.
"""

# RULE_SOURCE: НК РУз ст.223 (сокрытие, штраф 20%) vs ст.219 КоАО (БРВ-штраф)
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
        if ev.type == TaxEventType.PENALTY
        and ev.date.year == current_year
        and ev.material
    ]
    if not penalties:
        return None

    total = sum(
        (ev.amount.amount for ev in penalties if ev.amount is not None),
        Decimal("0"),
    )
    count = len(penalties)
    return FiringEvidence(
        message=f"Материальная пеня по налогам в {current_year} году: {count} шт., итого {total}",
        message_uz=(
            f"{current_year} yilida moddiy soliq penyalari: {count} ta, jami {total}"
        ),
        evidence={
            "count": count,
            "total_amount": str(total),
            "year": current_year,
        },
    )
