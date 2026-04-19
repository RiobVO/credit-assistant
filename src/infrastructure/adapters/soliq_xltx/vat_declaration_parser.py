"""Парсер «Расчёт НДС» (декларация НДС, 8 листов list01..list08).

Извлекает декларированные обороты по реализации с разбивкой по каналам
(ЭСФ / ККМ / экспорт / marketplace / прочие) и сумму НДС, начисленную и
подлежащую зачёту. Цель — закрыть правило ``VAT_ESF_MISMATCH`` в Day 2.

Координаты сверены с реальной выгрузкой папы (март 2026):
- list02 (Приложение №1): R6 итого по реализации (стр.010), R7-R11 разбивка
  по каналам (стр.0101..0105). Колонки: F стоимость, G сумма НДС.
- list04 (Приложение №3): R7 НДС к зачёту (нарастающий с начала года, стр.010),
  R37 НДС подлежащий зачёту (стр.040, col G).

Ячейки с символом 'x' (экспорт без НДС) → ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from domain.value_objects.money import Currency, Money
from infrastructure.adapters.soliq_xltx.errors import (
    MalformedXltxError,
    UnsupportedFormatError,
)
from infrastructure.adapters.soliq_xltx.format_detector import (
    SoliqXltxFormat,
    detect_format,
)
from infrastructure.adapters.soliq_xltx.header_parser import (
    SoliqXltxHeader,
    parse_header,
)


@dataclass(frozen=True, slots=True)
class VatDeclarationData:
    """Декларированные данные НДС за налоговый период.

    ``vat_charged_total`` — сумма НДС, начисленная за период (стр.010 list02 G6).
    Это же значение пойдёт в ``FinancialReport.vat_declared`` при сборке snapshot
    в Day 2.

    ``sales_via_*`` — стоимость без НДС по каналам реализации (стр.0101-0105 col F).
    ``*_vat`` — соответствующая сумма НДС (col G); может быть ``None`` для каналов,
    где Soliq ставит 'x' (например, экспорт по нулевой ставке).
    """

    header: SoliqXltxHeader
    sales_total_excl_vat: Money | None
    vat_charged_total: Money | None
    sales_via_esf: Money | None
    vat_via_esf: Money | None
    sales_via_kkm: Money | None
    vat_via_kkm: Money | None
    sales_via_export: Money | None
    vat_via_export: Money | None
    sales_via_marketplace: Money | None
    vat_via_marketplace: Money | None
    sales_via_other: Money | None
    vat_via_other: Money | None
    vat_to_offset_year_cumulative: Money | None
    vat_to_offset_total: Money | None


def parse_vat_declaration(wb: Workbook) -> VatDeclarationData:
    """Прочитать VAT-декларацию из openpyxl Workbook.

    Бросает ``UnsupportedFormatError``, если формат не VAT_DECLARATION.
    Бросает ``MalformedXltxError`` для критичных ячеек (list02/list04 отсутствуют).
    """
    fmt = detect_format(wb)
    if fmt is not SoliqXltxFormat.VAT_DECLARATION:
        raise UnsupportedFormatError(wb.sheetnames, f"expected VAT_DECLARATION, got {fmt}")

    header = parse_header(wb, fmt)
    if "list02" not in wb.sheetnames:
        raise UnsupportedFormatError(wb.sheetnames, "list02 missing in VAT declaration")
    if "list04" not in wb.sheetnames:
        raise UnsupportedFormatError(wb.sheetnames, "list04 missing in VAT declaration")

    list02 = wb["list02"]
    list04 = wb["list04"]

    return VatDeclarationData(
        header=header,
        sales_total_excl_vat=_money(list02, "F6"),
        vat_charged_total=_money(list02, "G6"),
        sales_via_esf=_money(list02, "F7"),
        vat_via_esf=_money(list02, "G7"),
        sales_via_kkm=_money(list02, "F8"),
        vat_via_kkm=_money(list02, "G8"),
        sales_via_export=_money(list02, "F9"),
        vat_via_export=_money(list02, "G9"),
        sales_via_marketplace=_money(list02, "F10"),
        vat_via_marketplace=_money(list02, "G10"),
        sales_via_other=_money(list02, "F11"),
        vat_via_other=_money(list02, "G11"),
        vat_to_offset_year_cumulative=_money(list04, "G7"),
        vat_to_offset_total=_money(list04, "G37"),
    )


def _money(ws: Worksheet, coord: str) -> Money | None:
    """Прочитать денежную сумму из ячейки.

    Возвращает ``None`` для пустых cells и для ячеек со значением 'x'/'Х'
    (Soliq использует X-маркер на полях, где значение неприменимо — например,
    НДС на экспорт по нулевой ставке).
    """
    raw = ws[coord].value
    if raw is None:
        return None
    if isinstance(raw, str):
        text = raw.strip()
        if text.lower() in ("x", "х", ""):  # Латинский x и кириллический Х
            return None
        try:
            return Money(Decimal(text.replace(",", ".")), Currency.UZS)
        except Exception as exc:
            raise MalformedXltxError(
                sheet=ws.title, coord=coord, reason=f"non-numeric money: {raw!r}"
            ) from exc
    if isinstance(raw, (int, float)):
        return Money(_decimal_from_number(raw), Currency.UZS)
    raise MalformedXltxError(
        sheet=ws.title, coord=coord, reason=f"unsupported money type: {type(raw)}"
    )


def _decimal_from_number(raw: Any) -> Decimal:
    """Конверсия numeric cell value в Decimal через str для сохранения точности."""
    return Decimal(str(raw))
