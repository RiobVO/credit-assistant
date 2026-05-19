"""LOAN_TO_REVENUE_RATIO: запрашиваемая сумма >40% годовой выручки."""

# RULE_SOURCE: IFC SME Banking Knowledge Guide (unsecured МСБ-baseline 0.30-0.40);
#   внутренние методики UZ-банков. ADR-0024: порог снижен 0.50 → 0.40 как
#   консервативный unsecured-default. Secured-вариант (порог 0.70) требует
#   поля `loan_request.collateral_type` — backlog post-Commit 5.
# CONFIDENCE: MEDIUM (industry practice / multilateral baseline)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

# ADR-0024: 0.50 → 0.40 per Claude Q0.B (IFC SME Banking Knowledge Guide
# рекомендует 0.30-0.40 для unsecured МСБ-baseline). Secured-уточнение
# до 0.70 — backlog (требует loan_request.collateral_type).
THRESHOLD = Decimal("0.4")


def loan_to_revenue_ratio(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    if snapshot.loan_request is None or not snapshot.annual_reports:
        return None

    # Берём последний по дате окончания отчёт
    latest = max(snapshot.annual_reports, key=lambda r: r.period.end)
    loan = snapshot.loan_request.amount.amount
    revenue = latest.revenue.amount

    if revenue <= 0:
        if loan <= 0:
            return None
        # Заём при нулевой выручке — фиксируем ratio=∞ через большое число
        return FiringEvidence(
            message=f"Запрашиваем {loan} при нулевой выручке за период",
            message_uz=f"Davr boʻyicha nol tushumda {loan} soʻralmoqda",
            evidence={"ratio": "infinity", "loan": str(loan), "annual_revenue": "0"},
        )

    ratio = loan / revenue
    if ratio <= THRESHOLD:
        return None
    return FiringEvidence(
        message=f"Сумма заёма {ratio:.0%} от годовой выручки",
        message_uz=f"Qarz summasi yillik tushumning {ratio:.0%}",
        evidence={"ratio": ratio, "loan": str(loan), "annual_revenue": str(revenue)},
    )
