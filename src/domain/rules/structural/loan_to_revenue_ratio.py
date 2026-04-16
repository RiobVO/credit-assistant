"""LOAN_TO_REVENUE_RATIO: запрашиваемая сумма >50% годовой выручки."""

# RULE_SOURCE: внутренние методики банков UZ; общая практика МСБ-кредитования
# CONFIDENCE: HIGH (industry-standard ratio)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

THRESHOLD = Decimal("0.5")


def loan_to_revenue_ratio(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    if snapshot.loan_request_amount is None or not snapshot.annual_reports:
        return None

    # Берём последний по дате окончания отчёт
    latest = max(snapshot.annual_reports, key=lambda r: r.period.end)
    loan = snapshot.loan_request_amount.amount
    revenue = latest.revenue.amount

    if revenue <= 0:
        if loan <= 0:
            return None
        # Заём при нулевой выручке — фиксируем ratio=∞ через большое число
        return FiringEvidence(
            message=f"Запрашиваем {loan} при нулевой выручке за период",
            evidence={"ratio": "infinity", "loan": str(loan), "annual_revenue": "0"},
        )

    ratio = loan / revenue
    if ratio <= THRESHOLD:
        return None
    return FiringEvidence(
        message=f"Сумма заёма {ratio:.0%} от годовой выручки",
        evidence={"ratio": ratio, "loan": str(loan), "annual_revenue": str(revenue)},
    )
