"""SHELL_COMPANY_PARTNERS: контрагенты с ИНН моложе 6 месяцев."""

# RULE_SOURCE: Group-IB Uzbekistan fraud report 2024-2025; AML compliance
# CONFIDENCE: HIGH (классическая схема фиктивной отчётности)
# VALIDATED_BY: []

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
    ]
    if not shells:
        return None

    return FiringEvidence(
        message=f"{len(shells)} контрагентов младше 6 мес",
        evidence={
            "shell_count": len(shells),
            "shell_inns": sorted(cp.inn.value for cp in shells),
        },
    )
