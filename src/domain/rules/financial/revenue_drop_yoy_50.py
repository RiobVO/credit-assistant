"""REVENUE_DROP_YOY_50: падение годовой выручки >50% год-к-году."""

# RULE_SOURCE: Altman Z-score / Iwanicz-Drozdowska et al. (JIFM 2017);
#   Базель III IRB approach. ADR-0024 убрал атрибуцию «ЦБ РУз №27-п» —
#   положение не подтверждено.
# CONFIDENCE: MEDIUM (industry practice / academic baseline)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

THRESHOLD = Decimal("-0.50")
# ADR-0024: minimum previous-year revenue, ниже которого падение −50%
# не имеет банковского значения (200 млн UZS ≈ stat.uz нижняя граница
# малого предприятия). Per Claude Q0.B audit.
PREV_REVENUE_MIN_THRESHOLD = Decimal("200000000")


def revenue_drop_yoy_50(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    if len(snapshot.annual_reports) < 2:
        return None

    sorted_reports = sorted(snapshot.annual_reports, key=lambda r: r.period.end)
    prev, curr = sorted_reports[-2], sorted_reports[-1]

    if prev.revenue.amount <= 0:
        return None
    # ADR-0024: материальность базы для YoY-расчёта.
    if prev.revenue.amount < PREV_REVENUE_MIN_THRESHOLD:
        return None

    yoy = (curr.revenue.amount - prev.revenue.amount) / prev.revenue.amount
    if yoy >= THRESHOLD:
        return None

    return FiringEvidence(
        message=f"Годовая выручка упала {yoy:.0%} YoY",
        message_uz=f"Yillik tushum {yoy:.0%} YoY pasaygan",
        evidence={
            "yoy_pct": str(yoy),
            "previous_year": prev.period.end.year,
            "current_year": curr.period.end.year,
            "previous_revenue": str(prev.revenue.amount),
            "current_revenue": str(curr.revenue.amount),
        },
    )
