"""LoadDossierReadiness: GET /api/dossier/{id}/readiness — зеркало для готового досье.

Зеркало для `assess_draft_readiness` (POST /api/manual-input/readiness), но
работает на **persisted** досье. Отличия:

* Грузит snapshot через ``DossierViewRepositoryPort`` (тот же port, что и
  `LoadDossierForView` — реюзаем существующий загрузчик).
* `source_trail` в snapshot **не хранится** — это draft-only концепция. Вместо
  него восстанавливаем `set[ParserSource]` через ``infer_parser_sources_from_snapshot``
  по присутствию полей: equity → FORM_1, profit_before_tax → FORM_2, и т.д.
  Heuristic, но достаточно надёжный для UI-сигнала «доверие к данным».

Возвращает None если досье не найдено — endpoint мапит в 404.
"""

from __future__ import annotations

from uuid import UUID

from application.ports.dossier_view_repository_port import DossierViewRepositoryPort
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.services.data_readiness import (
    DataReadinessReport,
    ParserSource,
    assess_readiness,
)


class LoadDossierReadiness:
    def __init__(self, repo: DossierViewRepositoryPort) -> None:
        self._repo = repo

    async def execute(self, dossier_id: UUID) -> DataReadinessReport | None:
        view = await self._repo.get_view_by_id(dossier_id)
        if view is None:
            return None
        sources = infer_parser_sources_from_snapshot(view.snapshot)
        return assess_readiness(view.snapshot, sources)


def infer_parser_sources_from_snapshot(snapshot: BorrowerSnapshot) -> set[ParserSource]:
    """Восстановить `set[ParserSource]` из persisted snapshot.

    `source_trail` теряется при persist (draft-only). Heuristic по наличию
    полей: какие парсеры могли заполнить эти данные. Цель — дать UI и domain
    `assess_readiness` информацию о покрытии (form1 для balance_ratios,
    esf/profit_tax для tax_burden capabilities).

    ``MANUAL`` добавляем всегда: досье существует → значит хоть какие-то
    данные были введены (через wizard или через парсер).
    """
    sources: set[ParserSource] = {ParserSource.MANUAL}

    annual = list(snapshot.annual_reports)
    quarterly = list(snapshot.quarterly_reports)

    # FORM_1 — balance sheet поля. Любое из equity / total_debt / assets /
    # liabilities × period_end или period_start. CA-037 расширил entity, всё
    # nullable; присутствие хотя бы одного → FORM_1 был источником.
    form1_fields = (
        "equity", "equity_period_start",
        "total_debt", "total_debt_period_start",
        "assets", "assets_period_start",
        "liabilities", "liabilities_period_start",
    )
    if any(
        getattr(r, fld, None) is not None
        for r in annual + quarterly
        for fld in form1_fields
    ):
        sources.add(ParserSource.FORM_1)

    # FORM_2 — income statement расширения (PBT, interest). CA-037 добавил,
    # nullable. Присутствие хотя бы одного → FORM_2 был.
    if any(
        r.profit_before_tax is not None or r.interest_expense is not None
        for r in annual + quarterly
    ):
        sources.add(ParserSource.FORM_2)

    # VAT_DECLARATION — vat_declared в VatPeriodReport.
    if any(v.vat_declared is not None for v in snapshot.vat_periods):
        sources.add(ParserSource.VAT_DECLARATION)

    # ESF_CSV — invoices или esf_seller_vat_total в vat_periods.
    if snapshot.invoices or any(
        v.esf_seller_vat_total is not None for v in snapshot.vat_periods
    ):
        sources.add(ParserSource.ESF_CSV)

    # PROFIT_TAX парсер ещё не подключён (TODO[CA-029b]). taxes_paid сейчас
    # приходит из manual ввода, поэтому не добавляем здесь по taxes_paid.
    # Когда CA-029b закроется — расширить эту функцию.

    return sources
