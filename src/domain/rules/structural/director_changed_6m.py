"""DIRECTOR_CHANGED_6M: смена директора за последние ~6 месяцев."""

# RULE_SOURCE: FATF Recommendation 24 (Beneficial Ownership); Закон РУз ЗРУ-660;
#   внутренние методики банков UZ. ADR-0024 уточнил source (был Group-IB UZ
#   LOW confidence, заменён на FATF R.24 + AML/CDD).
# CONFIDENCE: MEDIUM (industry practice / AML pattern)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

# 6 месяцев упрощаем как 180 дней, не calendar-точно (relativedelta — Phase 2)
WINDOW_DAYS = 180
# ADR-0024: minimum loan amount, ниже которого фронт-фигура не имеет
# экономического смысла. Per Claude Q0.B audit: смена директора +
# заявка <500 млн сум вероятнее operational change, не AML-pattern.
LOAN_AMOUNT_MIN_THRESHOLD = Decimal("500000000")


def director_changed_6m(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    days_since = (snapshot.as_of - snapshot.borrower.director_appointed_at).days
    if days_since > WINDOW_DAYS:
        return None
    # ADR-0024: подтверждение AML-сигнала через материальность заявки.
    loan = snapshot.loan_request
    if loan is None or loan.amount.amount < LOAN_AMOUNT_MIN_THRESHOLD:
        return None
    return FiringEvidence(
        message=f"Директор сменился {days_since} дней назад",
        message_uz=f"Direktor {days_since} kun oldin almashgan",
        evidence={
            "days_since_change": days_since,
            "loan_amount": str(loan.amount.amount),
        },
    )
