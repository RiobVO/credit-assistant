"""CIRCULAR_INVOICING: упрощённая 2-узловая детекция циклов A→B + B→A."""

# RULE_SOURCE: НК РУз гл. 17; EAG (Eurasian Group) typology reports;
#   Закон РУз ЗРУ-660 «О ПОД/ФТ». ADR-0024 убрал атрибуцию Group-IB UZ
#   и заменил на EAG VAT-carousel typology + НК РУз chapter 17.
# CONFIDENCE: MEDIUM (heuristic — 2-cycle only, без 3+ узлов; материальный
#   порог 100 млн UZS снижает ложноположительные)
# VALIDATED_BY: []
# TODO[CA-002]: полноценная детекция циклов через граф (networkx) для 3+ узлов

from collections import defaultdict
from decimal import Decimal

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.invoice import Invoice, InvoiceRole
from domain.rules.protocol import FiringEvidence

WINDOW_DAYS = 90
# ADR-0024: материальный порог пары sell+buy. Per Claude Q0.B: 100 млн
# UZS отделяет crowd-fraud VAT-carousel от рутинных bidirectional ЭСФ
# (subcontracting, factoring, mutual offsets). EAG typology guide
# фиксирует carousel-схемы как явление >$10K на цикл.
MIN_PAIR_VOLUME = Decimal("100000000")


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
        # Ищем хотя бы одну пару sell+buy внутри окна с совокупным объёмом
        # ≥ MIN_PAIR_VOLUME. Достаточно одной пары для cycle-flag.
        cycle_found = False
        for sell in sells:
            paired = next(
                (b for b in buys if abs((sell.date - b.date).days) <= WINDOW_DAYS),
                None,
            )
            if paired is None:
                continue
            pair_volume = sell.amount.amount + paired.amount.amount
            if pair_volume >= MIN_PAIR_VOLUME:
                cycles.append(cp_inn)
                cycle_found = True
                break
        if cycle_found:
            continue

    if not cycles:
        return None

    return FiringEvidence(
        message=f"Подозрение на циклические ЭСФ с {len(cycles)} контрагентами",
        message_uz=f"{len(cycles)} ta kontragent bilan tsiklik EHF shubhasi",
        evidence={
            "cycle_count": len(cycles),
            "counterparty_inns": sorted(cycles),
        },
    )
