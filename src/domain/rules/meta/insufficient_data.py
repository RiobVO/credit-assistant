"""INSUFFICIENT_DATA: snapshot не содержит ни одной точки выручки.

Срабатывает, когда у борровера нет ни annual reports, ни quarterly, ни monthly
turnover с положительной выручкой. Без этих данных ни одно из 17 финансовых/
контрагентных правил не может корректно сработать — скоринг возвращал бы
ложно-оптимистичный «0 flags = APPROVE» при пустых данных.

ScoringService применяет к этому флагу policy: domain score floor = 50
(display ≤ 50), recommendation force = REVIEW. Это защита от bias к одобрению
при недостаточности данных.
"""

# RULE_SOURCE: внутренняя политика — defensive default при пустом снапшоте
# CONFIDENCE: HIGH (data-quality safeguard)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

# Идентификатор используется ScoringService для применения policy.
INSUFFICIENT_DATA_RULE_ID = "INSUFFICIENT_DATA"


def insufficient_data(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    """Срабатывает если ни одна точка выручки не положительна."""
    if _has_any_positive_revenue(snapshot):
        return None

    return FiringEvidence(
        message="Недостаточно данных для оценки: нет ни одной точки выручки",
        message_uz="Baholash uchun maʼlumotlar yetarli emas: birorta tushum nuqtasi yoʻq",
        evidence={
            "annual_reports_count": len(snapshot.annual_reports),
            "quarterly_reports_count": len(snapshot.quarterly_reports),
            "monthly_turnover_count": len(snapshot.monthly_turnover),
        },
    )


def _has_any_positive_revenue(snapshot: BorrowerSnapshot) -> bool:
    zero = Decimal("0")
    return (
        any(r.revenue.amount > zero for r in snapshot.annual_reports)
        or any(r.revenue.amount > zero for r in snapshot.quarterly_reports)
        or any(m.revenue.amount > zero for m in snapshot.monthly_turnover)
    )
