"""Сборка ``SoliqChunk`` из пары парсеров: VAT-декларация + ilova-реестр.

Вход — два ``ParsedSoliqXltx`` объекта, относящихся к одному налоговому периоду
(обычно месяц). Выход — ``SoliqChunk`` с одним ``VatPeriodReport`` для этого
периода.

Месяц передаётся явным параметром ``period_month``: VAT-декларация Soliq не
содержит стабильной ячейки с номером месяца (только год в шапке + дата подачи),
а UI/API уровень знает за какой период загружается выгрузка. Это обсуждалось
в плане Day 2 — см. ADR 0006.

Контракт идентификации: ИНН в обоих файлах сверяется с ``borrower_inn``;
несовпадение поднимает ``ChunkBorrowerMismatchError`` на use case-уровне, поэтому
маппер сам ИНН-проверкой не занимается — он только отдаёт chunk с тем ИНН,
который пришёл из декларации (ilova собственного header не имеет).
"""

from __future__ import annotations

import calendar
from datetime import date

from application.dto.parsed_data_chunk import SoliqChunk
from domain.entities.vat_period_report import VatPeriodReport
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
from infrastructure.adapters.soliq_xltx.errors import MalformedXltxError
from infrastructure.adapters.soliq_xltx.vat_declaration_parser import VatDeclarationData
from infrastructure.adapters.soliq_xltx.vat_registry_parser import VatRegistryData


class XltxBorrowerMismatchError(ValueError):
    """ИНН в декларации не совпадает с ожидаемым заёмщиком."""

    def __init__(self, *, expected: INN, actual: INN) -> None:
        super().__init__(
            f"declaration belongs to INN {actual.masked}, expected {expected.masked}"
        )
        self.expected = expected
        self.actual = actual


def to_soliq_chunk(
    *,
    declaration: VatDeclarationData,
    registry: VatRegistryData,
    borrower_inn: INN,
    period_month: int,
) -> SoliqChunk:
    """Свернуть пару (декларация, реестр) в ``SoliqChunk`` с одним VAT-периодом.

    Бросает:
    - ``ValueError``, если ``period_month`` вне 1..12;
    - ``XltxBorrowerMismatchError``, если ИНН в декларации не равен ожидаемому;
    - ``MalformedXltxError``, если в декларации не задан год периода.
    """
    if not 1 <= period_month <= 12:
        raise ValueError(f"period_month must be in 1..12, got {period_month}")

    declaration_inn = declaration.header.borrower_inn
    if declaration_inn != borrower_inn:
        raise XltxBorrowerMismatchError(expected=borrower_inn, actual=declaration_inn)

    year = declaration.header.period_year
    if year <= 0:
        raise MalformedXltxError(
            sheet="list01",
            coord="<header>",
            reason=f"period_year must be positive, got {year}",
        )

    period = _month_range(year, period_month)
    vat_period = VatPeriodReport(
        period=period,
        vat_declared=declaration.vat_charged_total,
        esf_seller_vat_total=registry.sales_vat_total,
        submitted_at=declaration.header.submitted_at,
    )

    return SoliqChunk(
        borrower_inn=borrower_inn,
        vat_periods=[vat_period],
    )


def _month_range(year: int, month: int) -> DateRange:
    last_day = calendar.monthrange(year, month)[1]
    return DateRange(date(year, month, 1), date(year, month, last_day))
