"""REVENUE_DROP_MOM_30: падение выручки >30% месяц-к-месяцу два периода подряд."""

# RULE_SOURCE: Базель III SREP; FRB SR 11-7 / SR 26-02. ADR-0024 убрал
#   атрибуцию «ЦБ РУз №27-п» (положение не подтверждено).
# CONFIDENCE: MEDIUM (academic baseline + supervisory practice)
# VALIDATED_BY: []

from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

THRESHOLD = Decimal("-0.30")
# ADR-0024: сезонный фильтр для UZ-bookkeeping. Декабрь→январь→февраль —
# месяцы естественного спада: закрытие года, новогодние праздники, низкий
# инвентарь. Падение −30%+ MoM в этом окне ⇒ ложноположительный для
# непрерывного бизнеса. Per Claude Q0.B audit: рекомендован filter, без
# которого правило фолсит на агро (section A) и строительстве (F) +
# туризме (I), но section-данные ещё не в snapshot (см. backlog).
SEASONAL_TRANSITION_MONTHS = frozenset({12, 1, 2})


def revenue_drop_mom_30(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    months = sorted(snapshot.monthly_turnover, key=lambda m: m.month_start)
    if len(months) < 3:
        return None

    m1, m2, m3 = months[-3], months[-2], months[-1]
    if m1.revenue.amount <= 0 or m2.revenue.amount <= 0:
        return None

    # ADR-0024: если ЛЮБОЙ из трёх анализируемых месяцев попадает в
    # сезонный transition (12/01/02), правило молчит — спад не аномалия.
    if any(m.month_start.month in SEASONAL_TRANSITION_MONTHS for m in (m1, m2, m3)):
        return None

    mom_1 = (m2.revenue.amount - m1.revenue.amount) / m1.revenue.amount
    mom_2 = (m3.revenue.amount - m2.revenue.amount) / m2.revenue.amount

    if mom_1 >= THRESHOLD or mom_2 >= THRESHOLD:
        return None

    return FiringEvidence(
        message=f"Выручка падает 2 месяца подряд: {mom_1:.0%} и {mom_2:.0%}",
        message_uz=f"Tushum ketma-ket 2 oy pasaymoqda: {mom_1:.0%} va {mom_2:.0%}",
        evidence={
            "mom_1": str(mom_1),
            "mom_2": str(mom_2),
            "months": [
                m1.month_start.isoformat(),
                m2.month_start.isoformat(),
                m3.month_start.isoformat(),
            ],
        },
    )
