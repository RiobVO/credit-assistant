"""LOAN_TO_REVENUE_RATIO: запрашиваемая сумма vs годовая выручка.

ADR-0024 Session 3: secured-variant. До этого был единый порог 0.40
(consistent с IFC SME unsecured baseline). Теперь:
- `collateral_type in (None, 'none')` → порог 0.40 (unsecured).
- остальные ('real_estate' / 'movable' / 'guarantee' / 'other') →
  порог 0.70 (secured, банк имеет страховочную базу).

Conservative default: None трактуется как unsecured. Legacy данные
без явного collateral_type → строгий порог 0.40 (как до Session 3).
"""

# RULE_SOURCE: IFC SME Banking Knowledge Guide (unsecured МСБ-baseline 0.30-0.40,
#   secured loans 0.60-0.70); внутренние методики UZ-банков.
#   ADR-0024 Session 3: secured-variant добавлен.
# CONFIDENCE: HIGH (industry practice / multilateral baseline)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

# ADR-0024 Session 3 dual-threshold.
THRESHOLD_UNSECURED = Decimal("0.4")
THRESHOLD_SECURED = Decimal("0.7")


def loan_to_revenue_ratio(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    if snapshot.loan_request is None or not snapshot.annual_reports:
        return None

    # Берём последний по дате окончания отчёт
    latest = max(snapshot.annual_reports, key=lambda r: r.period.end)
    loan = snapshot.loan_request.amount.amount
    revenue = latest.revenue.amount

    # ADR-0024 Session 3: secured-variant порог. None и 'none' трактуются
    # одинаково (conservative — legacy data без явного collateral).
    collateral = snapshot.loan_request.collateral_type
    secured = collateral is not None and collateral != "none"
    threshold = THRESHOLD_SECURED if secured else THRESHOLD_UNSECURED

    if revenue <= 0:
        if loan <= 0:
            return None
        # Заём при нулевой выручке — фиксируем ratio=∞ через большое число
        return FiringEvidence(
            message=f"Запрашиваем {loan} при нулевой выручке за период",
            message_uz=f"Davr boʻyicha nol tushumda {loan} soʻralmoqda",
            evidence={
                "ratio": "infinity",
                "loan": str(loan),
                "annual_revenue": "0",
                "secured": secured,
            },
        )

    ratio = loan / revenue
    if ratio <= threshold:
        return None
    return FiringEvidence(
        message=f"Сумма заёма {ratio:.0%} от годовой выручки",
        message_uz=f"Qarz summasi yillik tushumning {ratio:.0%}",
        evidence={
            "ratio": ratio,
            "loan": str(loan),
            "annual_revenue": str(revenue),
            "secured": secured,
            "threshold": str(threshold),
        },
    )
