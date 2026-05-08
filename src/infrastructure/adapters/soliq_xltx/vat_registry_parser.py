"""Парсер ilova-приложения №4 к Расчёту НДС: реестр счетов-фактур построчно.

В отличие от CSV из e-factura.uz (parser в ``esf_csv``), этот файл содержит
**сумму НДС по каждой ЭСФ** — что и закрывает дилемму с ``esf_seller_vat_total``,
описанную в ADR 0004.

Структура (по реальной выгрузке папы, март 2026, 503 продажи + 53 закупки):
- list01 (Таблица №1, **закупки**): шапка R11, данные с R15. Колонки B-K.
- list02 (Таблица №2, **продажи**): шапка R11, данные с R15. Колонки B-K, плюс
  I = «Стоимость с НДС» = G + H.
- ИТОГО-строки (R13) могут содержать формулы =SUM(...); мы **игнорируем** их и
  считаем суммы НДС вручную по data rows.

Колонки data rows:
- B: №
- C: Наименование контрагента
- D: ИНН контрагента (опционально — пусто для розничных покупателей-ПИНФЛ)
- E: Номер счёта-фактуры
- F: Дата счёта-фактуры (формат DD.MM.YYYY либо datetime)
- G: Стоимость поставки без НДС
- H: Сумма НДС
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
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


@dataclass(frozen=True, slots=True)
class VatRegistryRow:
    seq_no: int
    counterparty_name: str
    counterparty_inn: str | None
    invoice_no: str
    invoice_date: date
    amount_excl_vat: Money
    vat_amount: Money


@dataclass(frozen=True, slots=True)
class VatRegistryData:
    """Декомпозиция реестра ЭСФ на закупки и продажи.

    ``sales_vat_total`` — сумма НДС по всем строкам ``sales`` (агрегат за период).
    Это и есть ``esf_seller_vat_total`` для домена в Day 2.
    """

    sales: list[VatRegistryRow] = field(default_factory=list)
    purchases: list[VatRegistryRow] = field(default_factory=list)
    sales_vat_total: Money = field(default_factory=lambda: Money(Decimal(0), Currency.UZS))
    purchases_vat_total: Money = field(default_factory=lambda: Money(Decimal(0), Currency.UZS))
    sales_amount_total: Money = field(default_factory=lambda: Money(Decimal(0), Currency.UZS))
    purchases_amount_total: Money = field(default_factory=lambda: Money(Decimal(0), Currency.UZS))


_DATA_START_ROW = 15


def parse_vat_registry(wb: Workbook) -> VatRegistryData:
    """Прочитать ilova-реестр (list01 + list02) с детализацией ЭСФ."""
    fmt = detect_format(wb)
    if fmt is not SoliqXltxFormat.VAT_REGISTRY_ILOVA:
        raise UnsupportedFormatError(wb.sheetnames, f"expected VAT_REGISTRY_ILOVA, got {fmt}")

    purchases = _read_rows(wb["list01"]) if "list01" in wb.sheetnames else []
    sales = _read_rows(wb["list02"]) if "list02" in wb.sheetnames else []

    sales_vat_total = _sum_money([r.vat_amount for r in sales])
    purchases_vat_total = _sum_money([r.vat_amount for r in purchases])
    sales_amount_total = _sum_money([r.amount_excl_vat for r in sales])
    purchases_amount_total = _sum_money([r.amount_excl_vat for r in purchases])

    return VatRegistryData(
        sales=sales,
        purchases=purchases,
        sales_vat_total=sales_vat_total,
        purchases_vat_total=purchases_vat_total,
        sales_amount_total=sales_amount_total,
        purchases_amount_total=purchases_amount_total,
    )


def _read_rows(ws: Worksheet) -> list[VatRegistryRow]:
    """Прочитать data rows реестра начиная с _DATA_START_ROW.

    Останавливается на первой пустой строке (B-cell None и C-cell None) — Soliq
    кладёт пустые строки-заполнители в конце листа.
    """
    rows: list[VatRegistryRow] = []
    max_row = ws.max_row
    for r in range(_DATA_START_ROW, max_row + 1):
        seq_raw = ws.cell(row=r, column=2).value
        name_raw = ws.cell(row=r, column=3).value
        if seq_raw is None and name_raw is None:
            # Пустая строка — пропуск (не break, потому что Soliq иногда оставляет
            # пробелы между блоками; но если оба cells подряд пустые — break).
            # На практике пустых блоков не встречалось — break безопасен.
            break
        rows.append(_parse_row(ws, r))
    return rows


def _parse_row(ws: Worksheet, r: int) -> VatRegistryRow:
    seq_no = _int_cell(ws, r, 2)
    name = _str_cell(ws, r, 3, required=True, row_no=r)
    inn = _str_cell(ws, r, 4, required=False, row_no=r)
    invoice_no = _str_cell(ws, r, 5, required=True, row_no=r)
    invoice_date = _date_cell(ws, r, 6)
    amount_excl_vat = _money_cell(ws, r, 7)
    vat_amount = _money_cell(ws, r, 8)
    return VatRegistryRow(
        seq_no=seq_no,
        counterparty_name=name,
        counterparty_inn=inn,
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        amount_excl_vat=amount_excl_vat,
        vat_amount=vat_amount,
    )


def _int_cell(ws: Worksheet, r: int, c: int) -> int:
    raw = ws.cell(row=r, column=c).value
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    raise MalformedXltxError(
        sheet=ws.title,
        coord=ws.cell(row=r, column=c).coordinate,
        reason=f"expected integer seq_no, got {raw!r}",
        row_no=r,
    )


def _str_cell(ws: Worksheet, r: int, c: int, *, required: bool, row_no: int) -> str | Any:
    raw = ws.cell(row=r, column=c).value
    if raw is None:
        if required:
            raise MalformedXltxError(
                sheet=ws.title,
                coord=ws.cell(row=r, column=c).coordinate,
                reason="required cell is empty",
                row_no=row_no,
            )
        return None
    text = str(raw).strip()
    if not text:
        if required:
            raise MalformedXltxError(
                sheet=ws.title,
                coord=ws.cell(row=r, column=c).coordinate,
                reason="required cell is empty",
                row_no=row_no,
            )
        return None
    return text


def _date_cell(ws: Worksheet, r: int, c: int) -> date:
    raw = ws.cell(row=r, column=c).value
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        try:
            return datetime.strptime(raw.strip(), "%d.%m.%Y").date()
        except ValueError as exc:
            raise MalformedXltxError(
                sheet=ws.title,
                coord=ws.cell(row=r, column=c).coordinate,
                reason=f"invalid date {raw!r} (expected DD.MM.YYYY)",
                row_no=r,
            ) from exc
    raise MalformedXltxError(
        sheet=ws.title,
        coord=ws.cell(row=r, column=c).coordinate,
        reason=f"invalid date type {type(raw)}",
        row_no=r,
    )


def _money_cell(ws: Worksheet, r: int, c: int) -> Money:
    raw = ws.cell(row=r, column=c).value
    if raw is None:
        return Money(Decimal(0), Currency.UZS)
    if isinstance(raw, str):
        text = raw.strip()
        if text == "":
            return Money(Decimal(0), Currency.UZS)
        try:
            return Money(Decimal(text.replace(",", ".")), Currency.UZS)
        except Exception as exc:
            raise MalformedXltxError(
                sheet=ws.title,
                coord=ws.cell(row=r, column=c).coordinate,
                reason=f"non-numeric money: {raw!r}",
                row_no=r,
            ) from exc
    if isinstance(raw, (int, float)):
        return Money(Decimal(str(raw)), Currency.UZS)
    raise MalformedXltxError(
        sheet=ws.title,
        coord=ws.cell(row=r, column=c).coordinate,
        reason=f"unsupported money type {type(raw)}",
        row_no=r,
    )


def _sum_money(values: list[Money]) -> Money:
    if not values:
        return Money(Decimal(0), Currency.UZS)
    total = Money(Decimal(0), Currency.UZS)
    for v in values:
        total = total + v
    return total
