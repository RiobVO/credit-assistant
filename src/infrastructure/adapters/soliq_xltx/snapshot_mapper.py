"""Сборка ``SoliqChunk`` из пары парсеров: VAT-декларация + ilova-реестр.

Вход — две Parsed* структуры, относящиеся к одному налоговому периоду
(обычно месяц). Выход — ``(SoliqChunk, parse_warnings)``: чанк с одним
``VatPeriodReport`` за этот период и агрегированный список best-effort
warnings из header, declaration body и registry.

Best-effort семантика (CA-014 hardening):
- ``parsed-INN отсутствует`` → НЕ raise (warn + skip сравнения, chunk собирается);
- ``parsed-INN ≠ user-INN`` → raise ``XltxBorrowerMismatchError`` (структурная
  защита: не принимаем файл другой компании);
- ``period_year отсутствует`` → fallback на текущий год + warn (downstream
  ожидает period с реальной датой);
- остальные cell-level warnings проброшены без изменения.

Месяц передаётся явным параметром ``period_month``: VAT-декларация Soliq не
содержит стабильной ячейки с номером месяца, а UI-уровень знает за какой
период загружается выгрузка. Обсуждалось в Day 2 — см. ADR 0006.
"""

from __future__ import annotations

import calendar
from datetime import date

from application.dto.parsed_data_chunk import SoliqChunk
from domain.entities.vat_period_report import VatPeriodReport
from domain.value_objects.date_range import DateRange
from domain.value_objects.inn import INN
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
) -> tuple[SoliqChunk, list[str]]:
    """Свернуть пару (декларация, реестр) в ``(SoliqChunk, parse_warnings)``.

    Бросает:
    - ``ValueError``, если ``period_month`` вне 1..12;
    - ``XltxBorrowerMismatchError``, если parsed-ИНН задан и не совпадает.

    Все остальные проблемы данных идут в parse_warnings — никаких raise.
    """
    if not 1 <= period_month <= 12:
        raise ValueError(f"period_month must be in 1..12, got {period_month}")

    warnings: list[str] = [
        *declaration.parse_warnings,
        *registry.parse_warnings,
    ]

    declaration_inn = declaration.header.borrower_inn
    if declaration_inn is None:
        warnings.append(
            "Не удалось верифицировать ИНН в шапке декларации — "
            "проверьте что загружен файл нужной фирмы"
        )
    elif declaration_inn != borrower_inn:
        raise XltxBorrowerMismatchError(expected=borrower_inn, actual=declaration_inn)

    year = declaration.header.period_year
    if year is None or year <= 0:
        fallback_year = date.today().year
        warnings.append(
            f"period year отсутствует в шапке — использован fallback {fallback_year}"
        )
        year = fallback_year

    period = _month_range(year, period_month)
    vat_period = VatPeriodReport(
        period=period,
        vat_declared=declaration.vat_charged_total,
        esf_seller_vat_total=registry.sales_vat_total,
        submitted_at=declaration.header.submitted_at,
    )

    chunk = SoliqChunk(
        borrower_inn=borrower_inn,
        vat_periods=[vat_period],
    )
    return chunk, warnings


def _month_range(year: int, month: int) -> DateRange:
    last_day = calendar.monthrange(year, month)[1]
    return DateRange(date(year, month, 1), date(year, month, last_day))
