"""AssessDraftReadinessUseCase — оценка готовности данных черновика для скоринга.

Stateless: вход — аналитический срез form state (какие годы заполнены и в
каком виде) + source_trail из multi-file автозаполнения; выход —
``DataReadinessReport`` от domain слоя. Никакого I/O, никакого чтения
персистенции. Sketch evaluation для UI Шага 3 wizard'а.

Архитектурное решение (см. ADR 0010): frontend сам анализирует form state
и шлёт «годы с annual / full quarters / partial quarters» — он точнее знает
структуру формы и реактивно обновляется при пользовательском вводе. Backend
из этого строит синтетический ``BorrowerSnapshot`` с минимально-валидными
FinancialReport-ами и вызывает domain.assess_readiness.

source_trail keys из ``POST /api/manual-input/parse-files`` (CA-027)
маппятся в ``ParserSource`` по prefix.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from domain.entities.borrower import Borrower, LegalForm
from domain.entities.borrower_snapshot import BorrowerSnapshot
from domain.entities.financial_report import FinancialReport
from domain.services.data_readiness import (
    DataReadinessReport,
    ParserSource,
    assess_readiness,
)
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from domain.value_objects.money import Currency, Money

# Префикс-маппинг ключей source_trail → ParserSource. Ключи приходят от
# adapter'ов (parse_manual_input_files / FORM_2 / VAT / FORM_1 wiring TODO).
# Порядок проверки: более специфичный prefix перед более общим (form1.* до
# generic revenue_/net_profit_).
_PREFIX_TO_SOURCE: tuple[tuple[str, ParserSource], ...] = (
    ("form1.", ParserSource.FORM_1),
    ("revenue_", ParserSource.FORM_2),
    ("net_profit_", ParserSource.FORM_2),
    ("vat_declared_", ParserSource.VAT_DECLARATION),
    ("esf_", ParserSource.ESF_CSV),
    ("profit_tax_", ParserSource.PROFIT_TAX),
)


@dataclass(frozen=True, slots=True)
class AssessDraftReadinessInput:
    """Аналитический срез form state Шага 2 wizard'а.

    Frontend derives эти списки из watched form values:
    - ``annual_report_years``: годы с непустым annual cell в revenue/netProfit
    - ``full_quarter_years``: годы с 4 заполненными квартальными cells
    - ``partial_quarter_years``: годы с ≥1 квартальной cell, но <4 (для
      попадания в ``years_covered`` без поднятия в ``full_years``)
    - ``source_trail``: память от parsed-files-dropzone (CA-027)
    """

    annual_report_years: list[int]
    full_quarter_years: list[int]
    partial_quarter_years: list[int]
    source_trail: dict[str, str]


def assess_draft_readiness(payload: AssessDraftReadinessInput) -> DataReadinessReport:
    """Вычислить readiness report для draft sketch.

    Pure-ish: I/O нет; единственные «нечистые» зависимости — конструкторы
    domain-entities, но они тоже pure-функции от primitives.
    """
    snapshot = _synthetic_snapshot(
        annual_years=payload.annual_report_years,
        full_quarter_years=payload.full_quarter_years,
        partial_quarter_years=payload.partial_quarter_years,
    )
    sources = source_trail_to_parser_sources(payload.source_trail)
    return assess_readiness(snapshot, sources)


def source_trail_to_parser_sources(
    source_trail: dict[str, str],
) -> set[ParserSource]:
    """Map source_trail keys → set[ParserSource] по prefix-match.

    Незнакомые ключи молча игнорируются — это устойчиво к будущим
    расширениям source_trail (новые форматы добавят свои ключи).
    """
    sources: set[ParserSource] = set()
    for key in source_trail:
        for prefix, source in _PREFIX_TO_SOURCE:
            if key.startswith(prefix):
                sources.add(source)
                break
    return sources


def _synthetic_snapshot(
    *,
    annual_years: list[int],
    full_quarter_years: list[int],
    partial_quarter_years: list[int],
) -> BorrowerSnapshot:
    """Минимально-валидный snapshot для assess_readiness.

    Содержимое FinancialReport (revenue/net_profit/taxes_paid) не важно для
    readiness — domain.assess_readiness смотрит только на наличие reports
    и их периоды. Money(1) UZS — фиктивная заглушка.

    ``partial_quarter_years`` представлены **одним** quarterly report на год
    (>1 но <4 — всё равно partial; domain считает full при >=4).
    """
    annual_reports = [_annual_report(y) for y in annual_years]
    quarterly_reports: list[FinancialReport] = []
    for year in full_quarter_years:
        quarterly_reports.extend(_quarterly_report(year, q) for q in range(1, 5))
    for year in partial_quarter_years:
        # Один partial quarter за год — достаточно чтобы попасть в years_covered.
        quarterly_reports.append(_quarterly_report(year, 1))

    return BorrowerSnapshot(
        borrower=_placeholder_borrower(),
        as_of=date.today(),
        annual_reports=annual_reports,
        quarterly_reports=quarterly_reports,
    )


def _annual_report(year: int) -> FinancialReport:
    return FinancialReport(
        period=DateRange(date(year, 1, 1), date(year, 12, 31)),
        revenue=_money_stub(),
        net_profit=_money_stub(),
        taxes_paid=_money_stub(),
    )


def _quarterly_report(year: int, quarter: int) -> FinancialReport:
    starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
    ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    return FinancialReport(
        period=DateRange(date(year, *starts[quarter]), date(year, *ends[quarter])),
        revenue=_money_stub(),
        net_profit=_money_stub(),
        taxes_paid=_money_stub(),
    )


def _money_stub() -> Money:
    return Money(Decimal(1), Currency.UZS)


def _placeholder_borrower() -> Borrower:
    """Borrower-заглушка: snapshot.borrower обязателен по invariant.

    Readiness assessment не читает данные заёмщика — это чистая структура
    «есть/нет периодов». Placeholder валидный по типам, но не имеет смысла
    как реальный заёмщик.
    """
    return Borrower(
        inn=INN("100000001"),
        name="<readiness-placeholder>",
        legal_form=LegalForm.LLC,
        registration_date=date(2000, 1, 1),
        director_name="<placeholder>",
        director_appointed_at=date(2000, 1, 1),
        okved_main="00.00",
        registered_address="<placeholder>",
    )
