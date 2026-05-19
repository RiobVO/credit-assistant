"""CIRCULAR_INVOICING: graph-based детекция циклов через networkx.

ADR-0024 / CA-002: переход с 2-node defaultdict-heuristic на полноценную
графовую детекцию. На текущем источнике данных (`BorrowerSnapshot.invoices`
хранит только наши ЭСФ — borrower является SELLER или BUYER) edges
всегда проходят через borrower → максимальный простой цикл длиной 2.
Когда появится источник cross-counterparty ЭСФ (CA-002b backlog —
внешний ESF graph через pilot bank или soliq.uz public ESF API), тот
же `_build_graph()` примет external invoices и `networkx.simple_cycles()`
найдёт 3+ node carousels без правок в детекторе.
"""

# RULE_SOURCE: НК РУз гл. 17; EAG (Eurasian Group) typology reports;
#   Закон РУз ЗРУ-660 «О ПОД/ФТ». ADR-0024 убрал атрибуцию Group-IB UZ
#   и заменил на EAG VAT-carousel typology + НК РУз chapter 17.
# CONFIDENCE: MEDIUM (graph-based, материальный порог 100 млн UZS;
#   3+ node detection активируется после CA-002b source data)
# VALIDATED_BY: []

from collections import defaultdict
from decimal import Decimal
from itertools import product

import networkx as nx

from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.invoice import Invoice, InvoiceRole
from domain.rules.protocol import FiringEvidence
from domain.value_objects.flag_severity import FlagSeverity

WINDOW_DAYS = 90
# ADR-0024: материальный порог цикла. Per Claude Q0.B: 100 млн UZS
# отделяет crowd-fraud VAT-carousel от рутинных bidirectional ЭСФ
# (subcontracting, factoring, mutual offsets). EAG typology guide
# фиксирует carousel-схемы как явление >$10K на цикл.
MIN_CYCLE_VOLUME = Decimal("100000000")

# (from_inn, to_inn) → invoices, агрегированные в этом ребре.
EdgeMap = dict[tuple[str, str], list[Invoice]]


def _build_graph(snapshot: BorrowerSnapshot) -> tuple[nx.DiGraph, EdgeMap]:
    """DiGraph поверх snapshot.invoices.

    SELLER edge: borrower → counterparty. BUYER edge: counterparty → borrower.
    Future (CA-002b): external invoices добавят CP_i → CP_j edges.
    """
    borrower_inn = snapshot.borrower.inn.value
    edges: EdgeMap = defaultdict(list)
    for inv in snapshot.invoices:
        cp_inn = inv.counterparty_inn.value
        if inv.our_role == InvoiceRole.SELLER:
            edges[(borrower_inn, cp_inn)].append(inv)
        else:
            edges[(cp_inn, borrower_inn)].append(inv)

    graph = nx.DiGraph()
    for frm, to in edges:
        graph.add_edge(frm, to)
    return graph, edges


def _qualifying_combo_total(cycle_edges: list[list[Invoice]]) -> Decimal | None:
    """Для каждого ребра цикла выбираем по одной invoice; ищем комбинацию,
    где даты лежат в окне WINDOW_DAYS и сумма ≥ MIN_CYCLE_VOLUME.

    Сложность O(∏|cycle_edges[i]|). На реальных данных |cycle|=2 и каждое
    ребро — handful invoices, комбинаторика приемлема.
    """
    for combo in product(*cycle_edges):
        dates = [inv.date for inv in combo]
        if (max(dates) - min(dates)).days > WINDOW_DAYS:
            continue
        total = sum((inv.amount.amount for inv in combo), Decimal(0))
        if total >= MIN_CYCLE_VOLUME:
            return total
    return None


def circular_invoicing(snapshot: BorrowerSnapshot) -> FiringEvidence | None:
    if not snapshot.invoices:
        return None

    graph, edges = _build_graph(snapshot)
    if graph.number_of_edges() == 0:
        return None

    borrower_inn = snapshot.borrower.inn.value
    qualifying_cycles: list[list[str]] = []

    for cycle_nodes in nx.simple_cycles(graph):
        if len(cycle_nodes) < 2:
            continue  # self-loop игнорируем
        # nx.simple_cycles отдаёт цикл как список узлов в порядке обхода:
        # [A, B, C] = A→B→C→A.
        cycle_edges: list[list[Invoice]] = []
        valid = True
        for i, frm in enumerate(cycle_nodes):
            to = cycle_nodes[(i + 1) % len(cycle_nodes)]
            invs = edges.get((frm, to))
            if not invs:
                valid = False
                break
            cycle_edges.append(invs)
        if not valid:
            continue
        if _qualifying_combo_total(cycle_edges) is not None:
            qualifying_cycles.append(cycle_nodes)

    if not qualifying_cycles:
        return None

    cp_inns: set[str] = set()
    for cycle_nodes in qualifying_cycles:
        for inn in cycle_nodes:
            if inn != borrower_inn:
                cp_inns.add(inn)
    max_cycle_length = max(len(c) for c in qualifying_cycles)

    # Session 3 severity override: 3+ узлов в простом цикле = VAT-carousel
    # с явной криминальной топологией (FATF R.21 + EAG typology). Эскалация
    # до CRITICAL поверх YAML high. 2-cycle сохраняет default (severity=None →
    # run_all возьмёт rule.severity=high из YAML — bidirectional pair как
    # рутинный сигнал).
    severity_override: FlagSeverity | None = (
        FlagSeverity.CRITICAL if max_cycle_length >= 3 else None
    )

    return FiringEvidence(
        message=f"Подозрение на циклические ЭСФ с {len(cp_inns)} контрагентами",
        message_uz=f"{len(cp_inns)} ta kontragent bilan tsiklik EHF shubhasi",
        evidence={
            "cycle_count": len(qualifying_cycles),
            "counterparty_inns": sorted(cp_inns),
            "max_cycle_length": max_cycle_length,
        },
        severity=severity_override,
    )
