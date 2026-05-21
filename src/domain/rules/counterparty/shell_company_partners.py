"""SHELL_COMPANY_PARTNERS: юр-лица-контрагенты с ИНН моложе 6 месяцев.

ADR-0024 Session 3: ИП (LegalForm.IE) исключаются — регистрация ИП в
Узбекистане занимает 1-2 дня, уставного капитала не требует, для частных
лиц нет требований по сроку существования. Молодой ИП = норма, не AML
red flag. Только юр-лица (ООО / АО / ЧП) с молодым ИНН + Counterparty с
неизвестным opf=None трактуются как подозрительные (conservative).
"""

# RULE_SOURCE: FATF Recommendation 10 (CDD) + 24 (Beneficial Ownership)
# Закон РУз ЗРУ-660 «О ПОД/ФТ»; EAG typology — shell-company misuse
# CONFIDENCE: HIGH (regulatory + industry-standard)
# VALIDATED_BY: []

from domain.entities.borrower import LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.rules.protocol import FiringEvidence

SHELL_AGE_MONTHS = 6


def shell_company_partners(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    all_partners: set[Counterparty] = set()
    for cp in snapshot.counterparties_buyers:
        all_partners.add(cp)
    for cp in snapshot.counterparties_suppliers:
        all_partners.add(cp)
    if not all_partners:
        return None

    shells = [
        cp
        for cp in all_partners
        if cp.months_since_registration(snapshot.as_of) < SHELL_AGE_MONTHS
        and cp.opf != LegalForm.IE
    ]
    if not shells:
        return None

    return FiringEvidence(
        message=f"{len(shells)} юр-лиц-контрагентов младше 6 мес",
        message_uz=f"6 oydan kichik {len(shells)} ta yuridik shaxs kontragent",
        evidence={
            "shell_count": len(shells),
            "shell_inns": sorted(cp.inn.value for cp in shells),
        },
    )
