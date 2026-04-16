"""CIRCULAR_INVOICING: упрощённая 2-узловая детекция циклов A→B + B→A."""

# RULE_SOURCE: Group-IB UZ fraud report 2024-2025; AML — накачивание оборота
# CONFIDENCE: LOW (heuristic — только 2-cycle, без 3+ узлов)
# VALIDATED_BY: []
# TODO[CA-002]: полноценная детекция циклов через граф (networkx) для 3+ узлов

from collections import defaultdict

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.invoice import Invoice, InvoiceRole
from domain.rules.protocol import FiringEvidence

WINDOW_DAYS = 90


def circular_invoicing(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    by_cp: dict[str, dict[InvoiceRole, list[Invoice]]] = defaultdict(
        lambda: {InvoiceRole.SELLER: [], InvoiceRole.BUYER: []},
    )
    for inv in snapshot.invoices:
        by_cp[inv.counterparty_inn.value][inv.our_role].append(inv)

    cycles: list[str] = []
    for cp_inn, by_role in by_cp.items():
        sells = by_role[InvoiceRole.SELLER]
        buys = by_role[InvoiceRole.BUYER]
        if not sells or not buys:
            continue
        # Достаточно одной пары в окне для одного контрагента
        for sell in sells:
            paired = next(
                (b for b in buys if abs((sell.date - b.date).days) <= WINDOW_DAYS),
                None,
            )
            if paired is not None:
                cycles.append(cp_inn)
                break

    if not cycles:
        return None

    return FiringEvidence(
        message=f"Подозрение на циклические ЭСФ с {len(cycles)} контрагентами",
        evidence={
            "cycle_count": len(cycles),
            "counterparty_inns": sorted(cycles),
        },
    )
