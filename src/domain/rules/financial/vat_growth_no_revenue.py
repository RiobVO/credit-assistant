"""VAT_GROWTH_NO_REVENUE: рост НДС-обязательств без роста выручки."""

# RULE_SOURCE: НК РУз; внутренние методики Soliq + банковская практика
# CONFIDENCE: MEDIUM (industry practice, threshold эвристика)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

VAT_GROWTH_THRESHOLD = Decimal("0.20")  # рост НДС >20%
REVENUE_GROWTH_CEILING = Decimal("0")  # выручка не растёт (≤0)


def vat_growth_no_revenue(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    months = sorted(snapshot.monthly_turnover, key=lambda m: m.month_start)
    if len(months) < 3:
        return None

    first, _, last = months[-3], months[-2], months[-1]

    if first.vat_obligations is None or last.vat_obligations is None:
        return None
    if first.vat_obligations.amount <= 0 or first.revenue.amount <= 0:
        return None

    vat_growth = (
        last.vat_obligations.amount - first.vat_obligations.amount
    ) / first.vat_obligations.amount
    revenue_growth = (last.revenue.amount - first.revenue.amount) / first.revenue.amount

    if vat_growth < VAT_GROWTH_THRESHOLD:
        return None
    if revenue_growth > REVENUE_GROWTH_CEILING:
        return None

    return FiringEvidence(
        message=f"НДС вырос {vat_growth:.0%} при росте выручки {revenue_growth:.0%}",
        message_uz=f"QQS {vat_growth:.0%} oʻsdi, tushum esa {revenue_growth:.0%} ga oʻsgan",
        evidence={
            "vat_growth_pct": str(vat_growth),
            "revenue_growth_pct": str(revenue_growth),
            "window_months": [first.month_start.isoformat(), last.month_start.isoformat()],
        },
    )
