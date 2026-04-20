"""PDF-aggregator: собирает разделы D и E из ``BorrowerSnapshot``.

Раздел D (контрагенты) и раздел E (налоговая дисциплина) — view-only агрегаты,
которых нет в KPI-bundle. Считаем их отдельным сервисом, чтобы сохранить
``compute_kpis`` тонким (он отвечает за карточки KPI на экране).

Все функции — чистые, без I/O, тестируются юнитом без БД.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from application.dto.dossier_pdf_bundle import (
    CounterpartyShare,
    TaxDelayEntry,
    TaxSummary,
)
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.counterparty import Counterparty
from domain.entities.tax_event import TaxEventType
from domain.value_objects.money import Currency, Money

NEW_COUNTERPARTY_THRESHOLD_MONTHS = 6
TAX_SUMMARY_WINDOW_YEARS = 3
TAX_FREEZE_WINDOW_DAYS = 365


def compute_top_buyers(
    snapshot: BorrowerSnapshot, *, limit: int = 10
) -> tuple[CounterpartyShare, ...]:
    """Топ-N покупателей по доле в выручке.

    Возвращает только тех контрагентов, которые есть и в ``counterparties_buyers``,
    и в ``buyer_revenue_share`` — иначе нечего показать в строке таблицы.
    """
    return _compute_top_shares(
        directory=snapshot.counterparties_buyers,
        share_map=snapshot.buyer_revenue_share,
        as_of=snapshot.as_of,
        limit=limit,
    )


def compute_top_suppliers(
    snapshot: BorrowerSnapshot, *, limit: int = 10
) -> tuple[CounterpartyShare, ...]:
    """Топ-N поставщиков по доле в закупках."""
    return _compute_top_shares(
        directory=snapshot.counterparties_suppliers,
        share_map=snapshot.supplier_purchase_share,
        as_of=snapshot.as_of,
        limit=limit,
    )


def _compute_top_shares(
    *,
    directory: list[Counterparty],
    share_map: dict[str, Decimal],
    as_of: date,
    limit: int,
) -> tuple[CounterpartyShare, ...]:
    by_inn = {cp.inn.value: cp for cp in directory}
    rows: list[CounterpartyShare] = []
    for inn, share in share_map.items():
        cp = by_inn.get(inn)
        if cp is None:
            continue
        months = cp.months_since_registration(as_of)
        rows.append(
            CounterpartyShare(
                inn=inn,
                name=cp.name,
                share_pct=(share * Decimal(100)),
                months_since_registration=months,
                is_new=months < NEW_COUNTERPARTY_THRESHOLD_MONTHS,
            ),
        )
    rows.sort(key=lambda r: r.share_pct, reverse=True)
    return tuple(rows[:limit])


def compute_tax_summary(snapshot: BorrowerSnapshot) -> TaxSummary:
    """Раздел E: просрочки, штрафы, блокировки счёта.

    Окна:
    * просрочки и штрафы — последние ``TAX_SUMMARY_WINDOW_YEARS`` лет до ``as_of``;
    * блокировки счёта — последние ``TAX_FREEZE_WINDOW_DAYS`` дней (правило
      BANK_ACCOUNT_FROZEN_12M из rules engine).
    """
    as_of = snapshot.as_of
    window_start_3y = as_of.replace(year=as_of.year - TAX_SUMMARY_WINDOW_YEARS)
    window_start_freeze = as_of - timedelta(days=TAX_FREEZE_WINDOW_DAYS)

    delays: list[TaxDelayEntry] = []
    penalties_total: Money | None = None
    freezes_count = 0

    for event in snapshot.tax_events:
        if event.type == TaxEventType.PAYMENT and event.date >= window_start_3y:
            if event.delay_days is not None and event.delay_days > 0:
                delays.append(
                    TaxDelayEntry(
                        paid_on=event.date,
                        delay_days=event.delay_days,
                        amount=event.amount,
                    ),
                )
        elif event.type == TaxEventType.PENALTY and event.date >= window_start_3y:
            if event.amount is not None:
                penalties_total = (
                    event.amount
                    if penalties_total is None
                    else penalties_total + event.amount
                )
        elif (
            event.type == TaxEventType.ACCOUNT_FREEZE
            and event.date >= window_start_freeze
        ):
            freezes_count += 1

    delays.sort(key=lambda d: d.paid_on, reverse=True)
    max_delay = max((d.delay_days for d in delays), default=0)

    if penalties_total is None and any(
        e.type == TaxEventType.PENALTY and e.amount is not None for e in snapshot.tax_events
    ):
        # Все penalty были вне 3-летнего окна — fallback на нулевое значение в UZS,
        # чтобы шаблон мог отрисовать «0 сум» вместо «нет данных».
        penalties_total = Money(Decimal(0), Currency.UZS)

    return TaxSummary(
        delays=tuple(delays),
        max_delay_days=max_delay,
        penalties_total=penalties_total,
        account_freezes_count_12m=freezes_count,
        has_freezes_12m=freezes_count > 0,
    )
