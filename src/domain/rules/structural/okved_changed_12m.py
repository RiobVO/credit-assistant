"""OKVED_CHANGED_12M: смена ОКЭД собственником за последние 12 месяцев.

ADR-0024 Session 3: narrow scope. Правило стреляет только когда смена
ОКЭД помечена `oked_changed_by_owner=True` — это инициатива заёмщика
(AML/CDD risk indicator). Госкомстат auto-overwrite (массовая
перекатегоризация без участия заёмщика) — silent: операционное событие,
не credit-risk. Default `oked_changed_by_owner=False` → правило silent
на всех 49 existing borrowers + brand-new dossiers через wizard.
"""

# RULE_SOURCE: Постановление КМ РУз №275 от 24.08.2016 (UZ-ОКЭД);
# FATF Recommendation 10 (CDD); внутренние методики UZ-банков
# CONFIDENCE: HIGH (regulatory + industry practice)
# VALIDATED_BY: []

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.rules.protocol import FiringEvidence

WINDOW_DAYS = 365


def okved_changed_12m(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    borrower = snapshot.borrower
    # ADR-0024 Session 3: silent если смена ОКЭД не инициирована собственником
    # (Госкомстат auto-overwrite, default-False legacy данные).
    if not borrower.oked_changed_by_owner:
        return None
    changed_at = borrower.okved_main_changed_at
    if changed_at is None:
        return None
    days_since = (snapshot.as_of - changed_at).days
    if days_since > WINDOW_DAYS:
        return None
    return FiringEvidence(
        message=f"Основной ОКЭД сменился собственником {days_since} дней назад",
        message_uz=f"Asosiy ОКЭД egasi tomonidan {days_since} kun oldin almashgan",
        evidence={"days_since_change": days_since, "current_okved": borrower.okved_main},
    )
